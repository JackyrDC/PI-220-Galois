import sys
import io
import json
import os

from lmf import db


def get_transitive_groups(degree: int) -> list[dict]:
    """
    Returns all transitive groups of the given degree with all available
    fields from the LMFDB gps_transitive table.
    """
    all_fields = [
        'label', 'pretty', 'name', 'n', 't', 'order',
        'parity', 'solv', 'ab', 'cyc', 'prim', 'nilpotency',
        'transitivity', 'num_conj_classes', 'auts', 'arith_equiv',
        'gapid', 'gapidfull', 'abstract_label', 'aut_label',
        'isomorphism', 'gens', 'subfields', 'siblings', 'quotients',
        'moddecompuniq', 'bound_quotients', 'bound_siblings',
        'malle_ainv', 'malle_b', 'malle_wang_b', 'malle_turkelli_b',
        'malle_c', 'malle_d', 'malle_status', 'malle_b_status',
        'concentrated', 'semiconcentrated', 'concentrated_core',
        'semiconcentrated_cores', 'concentrated_abelian',
        'semiconcentrated_abelian', 'concentrated_nilpotent',
    ]

    results = list(db.gps_transitive.search(
        {'n': degree},
        projection=all_fields,
        sort=['t'],
    ))

    return results


def _yn(value) -> str:
    if value is None:
        return 'N/D'
    return 'Sí' if value else 'No'


def display_groups(groups: list[dict]) -> None:
    degree = groups[0].get('n', '?') if groups else '?'
    print(f"Grupos transitivos de grado {degree}: {len(groups)} encontrados\n")

    for g in groups:
        parity = g.get('parity')
        parity_str = {1: 'par (+1)', -1: 'impar (-1)'}.get(parity, 'N/D')
        nilpotency = g.get('nilpotency')
        if nilpotency is None:
            nilpotency_str = 'N/D'
        elif nilpotency == -1:
            nilpotency_str = 'No nilpotente'
        else:
            nilpotency_str = nilpotency

        print(f"{'='*60}")
        print(f"Label       : {g.get('label', 'N/D')}")
        print(f"Nombre      : {g.get('pretty', 'N/D')}  ({g.get('name', 'N/D')})")
        print(f"Orden       : {g.get('order', 'N/D')}")
        print(f"GAP id      : {g.get('gapidfull', 'N/D')}")
        print(f"Abstract    : {g.get('abstract_label', 'N/D')}")
        print(f"Paridad     : {parity_str}")
        print(f"Soluble     : {_yn(g.get('solv'))}")
        print(f"Abeliano    : {_yn(g.get('ab'))}")
        print(f"Cíclico     : {_yn(g.get('cyc'))}")
        print(f"Primitivo   : {_yn(g.get('prim'))}")
        print(f"Nilpotencia : {nilpotency_str}")
        print(f"Transitividad: {g.get('transitivity', 'N/D')}")
        print(f"Clases conj.: {g.get('num_conj_classes', 'N/D')}")
        print(f"Automorfismos: {g.get('auts', 'N/D')}")
        print(f"Equiv. arit.: {g.get('arith_equiv', 'N/D')}")
        print(f"Subcuerpos  : {g.get('subfields', 'N/D')}")
        print(f"Siblings    : {g.get('siblings', 'N/D')}")
        print(f"Cocientes   : {g.get('quotients', 'N/D')}")
        print(f"Generadores : {g.get('gens', 'N/D')}")
        print(f"Malle a_inv : {g.get('malle_ainv', 'N/D')}")
        print(f"Malle b     : {g.get('malle_b', 'N/D')}")
        print(f"Malle c     : {g.get('malle_c', 'N/D')}")
        print(f"Malle d     : {g.get('malle_d', 'N/D')}")
    print(f"{'='*60}")


def output_dir(degree: int) -> str:
    """Returns the output folder for a given degree, creating it if needed."""
    path = str(degree)
    os.makedirs(path, exist_ok=True)
    return path


def save_groups_json(groups: list[dict], degree: int) -> str:
    """Saves the groups to a JSON file (inside the degree's output folder)
    and returns the file path."""
    path = f"{output_dir(degree)}/transitive_groups_n{degree}.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(groups, f, ensure_ascii=False, indent=2)
    return path


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    degree = int(input("Introduce el grado: "))
    groups = get_transitive_groups(degree)

    if not groups:
        print(f"No se encontraron grupos transitivos de grado {degree}.")
    else:
        display_groups(groups)
        json_path = save_groups_json(groups, degree)
        print(f"\nDatos guardados en {json_path}")
