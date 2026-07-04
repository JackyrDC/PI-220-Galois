"""
Unifies the full pipeline for a given degree n:
  1. Fetch all transitive groups of degree n from LMFDB (collect_db.py)
  2. Find a defining polynomial for each group in LMFDB (find_polynomials.py)
  3. Independently compute/verify each Galois group with SageMath in WSL
     (verify_with_sage.py)

Usage:
    python run_pipeline.py <degree>

Requires WSL with a SageMath conda environment named "sage". If missing,
run setup_sage_wsl.ps1 first.
"""

import sys
import io
import json
import subprocess
import atexit
import logging

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import collect_db
import find_polynomials


def _close_lmf_log_handlers() -> None:
    """Release file handles opened by lmf/psycodict's slow-query logger.

    On Windows, lmf's atexit cleanup deletes its temp folder (which holds
    slow.log) but never closes the FileHandler writing to it, so the delete
    fails with a (harmless) PermissionError. Closing the handlers first,
    via an atexit callback registered after lmf's own, runs before it
    (atexit is LIFO) and lets the cleanup succeed silently.
    """
    for logger in list(logging.Logger.manager.loggerDict.values()):
        if isinstance(logger, logging.Logger):
            for handler in logger.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    logger.removeHandler(handler)


atexit.register(_close_lmf_log_handlers)

SAGE_SCRIPT = 'verify_with_sage.py'


def list_wsl_distros() -> list[str]:
    """Returns the names of all installed WSL distros."""
    result = subprocess.run(
        ['wsl.exe', '-l', '-q'],
        capture_output=True,
    )
    if result.returncode != 0:
        return []
    names = result.stdout.decode('utf-16-le', errors='ignore').splitlines()
    return [n.strip() for n in names if n.strip()]


def get_wsl_distro() -> str | None:
    """Returns the name of the first installed WSL distro with a ready
    SageMath conda environment, or None if none qualify."""
    for name in list_wsl_distros():
        if sage_env_ready(name):
            return name
    return None


def sage_env_ready(distro: str) -> bool:
    result = subprocess.run(
        ['wsl.exe', '-d', distro, '--', 'bash', '-lc',
         'source "$HOME/miniforge3/etc/profile.d/conda.sh" 2>/dev/null && '
         'conda activate sage 2>/dev/null && sage --version'],
        capture_output=True,
    )
    return result.returncode == 0


def to_wsl_path(distro: str, windows_path: str) -> str:
    result = subprocess.run(
        ['wsl.exe', '-d', distro, '--', 'wslpath', '-a', windows_path],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def run_sage_verification(distro: str, in_name: str, out_name: str) -> None:
    work_dir = to_wsl_path(distro, '.')
    command = (
        'source "$HOME/miniforge3/etc/profile.d/conda.sh" && conda activate sage && '
        f'cd "{work_dir}" && sage {SAGE_SCRIPT} "{in_name}" "{out_name}"'
    )
    subprocess.run(['wsl.exe', '-d', distro, '--', 'bash', '-lc', command], check=True)


def main(degree: int) -> None:
    print(f"[1/3] Descargando grupos transitivos de grado {degree} desde LMFDB...", flush=True)
    groups = collect_db.get_transitive_groups(degree)
    if not groups:
        print(f"No se encontraron grupos transitivos de grado {degree}.", flush=True)
        return
    out_dir = collect_db.output_dir(degree)
    groups_path = collect_db.save_groups_json(groups, degree)
    print(f"  {len(groups)} grupos guardados en {groups_path}", flush=True)

    print(f"\n[2/3] Descargando TODOS los cuerpos numericos de LMFDB para grado {degree} (sin limite)...", flush=True)
    full_path = f'{out_dir}/nf_fields_n{degree}.json'
    representatives, counts = find_polynomials.download_all_fields(degree, full_path)
    total_fields = sum(counts.values())
    print(f"  {total_fields} cuerpos numericos descargados en {full_path}", flush=True)

    dataset = find_polynomials.build_polynomial_dataset(degree, groups, representatives)
    poly_name = f'{out_dir}/galois_polynomials_n{degree}.json'
    with open(poly_name, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    found = sum(1 for e in dataset if e['coeffs'])
    print(f"  {found}/{len(dataset)} grupos con representante. Guardado en {poly_name}", flush=True)

    print(f"\n[3/3] Verificando/calculando grupos de Galois con SageMath (WSL)...", flush=True)
    distro = get_wsl_distro()
    if not distro:
        print("SageMath no esta listo en WSL.", flush=True)
        print("Ejecuta primero: powershell -File setup_sage_wsl.ps1", flush=True)
        return

    final_name = f'{out_dir}/galois_polynomials_n{degree}_final.json'
    run_sage_verification(distro, poly_name, final_name)

    with open(final_name, encoding='utf-8') as f:
        final_dataset = json.load(f)
    verified = sum(1 for e in final_dataset if e.get('sage_verified'))
    print(f"\nListo. {verified}/{len(final_dataset)} verificados. Resultado final en {final_name}", flush=True)


if __name__ == '__main__':
    degree = int(sys.argv[1]) if len(sys.argv) > 1 else int(input("Introduce el grado: "))
    main(degree)
