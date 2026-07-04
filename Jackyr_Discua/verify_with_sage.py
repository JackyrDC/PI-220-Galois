"""
Runs inside the SageMath conda environment (WSL). Reads the polynomials
found in LMFDB (galois_polynomials_n8.json), and for each one independently
computes its Galois group with Sage to verify it matches the transitive
group reported by LMFDB. For any group still missing a polynomial, attempts
a bounded random search for one with a matching Galois group.

Usage (inside the sage env):
    sage -python verify_with_sage.py <input.json> <output.json>
"""

import json
import sys
import random

from cysignals.signals import AlarmInterrupt

R = PolynomialRing(QQ, 'x')
x = R.gen()


def compute_galois_group(coeffs, timeout=120):
    """Independently computes order and transitive number for a polynomial
    given as a list of coefficients [a0, a1, ..., an]."""
    f = R(coeffs)
    if not f.is_irreducible():
        return {'error': 'no es irreducible'}

    alarm(timeout)
    try:
        G = f.galois_group()
        return {
            'order': int(G.order()),
            'transitive_number': int(G.transitive_number()),
        }
    except AlarmInterrupt:
        return {'error': f'timeout ({timeout}s)'}
    except Exception as e:
        return {'error': str(e)}
    finally:
        cancel_alarm()


def random_search(degree, target_t, target_order, attempts=200, coeff_range=4, timeout=15):
    """Bounded random search for a degree-n polynomial whose Galois group
    is the transitive group nT<target_t>. Only worth attempting for small
    groups; skipped (returns None) for large orders where this is hopeless."""
    if target_order > 200:
        return None

    for _ in range(attempts):
        coeffs = [random.randint(-coeff_range, coeff_range) for _ in range(degree)] + [1]
        if coeffs[0] == 0:
            continue
        f = R(coeffs)
        if not f.is_irreducible():
            continue
        alarm(timeout)
        try:
            G = f.galois_group()
            if int(G.transitive_number()) == target_t:
                return coeffs
        except AlarmInterrupt:
            pass
        except Exception:
            pass
        finally:
            cancel_alarm()
    return None


def main(in_path, out_path):
    with open(in_path, encoding='utf-8') as f:
        dataset = json.load(f)

    for entry in dataset:
        degree = entry['n']
        t = entry['t']

        if entry.get('coeffs'):
            result = compute_galois_group(entry['coeffs'], timeout=120)
            entry['sage_computation'] = result
            entry['sage_verified'] = result.get('transitive_number') == t
            print(f"{entry['label']}: {result}", flush=True)
        else:
            found = random_search(degree, t, entry.get('order', 10**9))
            if found:
                entry['coeffs'] = found
                entry['source'] = 'sage_random_search'
                entry['sage_verified'] = True
                print(f"{entry['label']}: encontrado por busqueda aleatoria -> {found}", flush=True)
            else:
                entry['sage_verified'] = False
                print(f"{entry['label']}: no encontrado (ni LMFDB ni busqueda aleatoria)", flush=True)

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    verified = sum(1 for e in dataset if e.get('sage_verified'))
    print(f"\n{verified}/{len(dataset)} verificados/encontrados con Sage. Guardado en {out_path}")


in_path = sys.argv[1] if len(sys.argv) > 1 else 'galois_polynomials_n8.json'
out_path = sys.argv[2] if len(sys.argv) > 2 else 'galois_polynomials_n8_final.json'
main(in_path, out_path)
