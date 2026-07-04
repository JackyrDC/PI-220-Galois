import sys
import io
import json

from lmf import db

import collect_db


def download_all_fields(
    degree: int, out_path: str, progress_every: int = 50000,
) -> tuple[dict[int, dict], dict[int, int]]:
    """
    Streams every LMFDB nf_fields record of the given degree (all Galois
    groups, all 42 columns, no row limit) straight to out_path as a JSON
    array, without buffering the whole result set in memory.

    Returns (representatives, counts):
      - representatives: {galt: first record found for that galt}, i.e. the
        smallest-label field for each group (results come sorted by
        (galt, label)). Used to pick one polynomial per group for the
        Sage-verification step.
      - counts: {galt: number of nf_fields records found for that group}
    """
    representatives: dict[int, dict] = {}
    counts: dict[int, int] = {}
    total = 0

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('[\n')
        first = True
        for row in db.nf_fields.search(
            {'degree': degree}, projection=2, sort=['galt', 'label'],
        ):
            galt = row['galt']
            counts[galt] = counts.get(galt, 0) + 1
            if galt not in representatives:
                representatives[galt] = row

            if not first:
                f.write(',\n')
            first = False
            f.write(json.dumps(row, ensure_ascii=False))

            total += 1
            if total % progress_every == 0:
                print(
                    f"  ...{total} cuerpos descargados (grado {degree}, "
                    f"grupo actual {degree}T{galt})", flush=True,
                )
        f.write('\n]\n')

    print(f"  {total} cuerpos numericos descargados en total para grado {degree}.", flush=True)
    return representatives, counts


def build_polynomial_dataset(
    degree: int, groups: list[dict], representatives: dict[int, dict],
) -> list[dict]:
    dataset = []
    for g in groups:
        t = g['t']
        entry = {
            'label': g['label'],
            'n': degree,
            't': t,
            'pretty': g.get('pretty'),
            'order': g.get('order'),
        }
        nf = representatives.get(t)
        if nf:
            entry['source'] = 'lmfdb'
            entry['nf_label'] = nf['label']
            entry['coeffs'] = nf['coeffs']
            print(f"{entry['label']}: {nf['label']} -> {nf['coeffs']}", flush=True)
        else:
            entry['source'] = None
            entry['nf_label'] = None
            entry['coeffs'] = None
            print(f"{entry['label']}: sin polinomio en LMFDB", flush=True)
        dataset.append(entry)
    return dataset


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    degree = int(sys.argv[1]) if len(sys.argv) > 1 else int(input("Introduce el grado: "))
    out_dir = collect_db.output_dir(degree)

    with open(f'{out_dir}/transitive_groups_n{degree}.json', encoding='utf-8') as f:
        groups = json.load(f)

    full_path = f'{out_dir}/nf_fields_n{degree}.json'
    print(f"Descargando TODOS los cuerpos numericos de grado {degree} desde LMFDB (sin limite)...", flush=True)
    representatives, counts = download_all_fields(degree, full_path)

    dataset = build_polynomial_dataset(degree, groups, representatives)

    out_path = f'{out_dir}/galois_polynomials_n{degree}.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    found = sum(1 for e in dataset if e['coeffs'])
    total_fields = sum(counts.values())
    print(f"{total_fields} cuerpos numericos descargados en {full_path}")
    print(f"{found}/{len(dataset)} grupos con polinomio encontrado en LMFDB.")
    print(f"Representantes guardados en {out_path}")

    missing = [e['label'] for e in dataset if not e['coeffs']]
    if missing:
        print(f"Sin polinomio en LMFDB (se intentara calcular con Sage): {missing}")
