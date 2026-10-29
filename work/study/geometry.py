"""Geometry primitives. Correspondences must come from input chemistry/sequence."""
import numpy as np

def xyz(values):
    result = np.asarray(values, dtype=float)
    if result.ndim != 2 or result.shape[1] != 3 or not np.isfinite(result).all():
        raise ValueError('Expected finite N by 3 coordinates')
    return result

def rigid_fit(moving, fixed):
    moving, fixed = xyz(moving), xyz(fixed)
    if moving.shape != fixed.shape or len(moving) < 3:
        raise ValueError('Need at least three corresponding points')
    center_m, center_f = moving.mean(axis=0), fixed.mean(axis=0)
    x, y = moving-center_m, fixed-center_f
    if np.linalg.matrix_rank(x) < 2 or np.linalg.matrix_rank(y) < 2:
        raise ValueError('Degenerate receptor alignment')
    u, _, vt = np.linalg.svd(x.T @ y)
    correction = np.eye(3)
    correction[-1,-1] = 1 if np.linalg.det(u @ vt) > 0 else -1
    rotation = u @ correction @ vt
    translation = center_f-center_m @ rotation
    return rotation, translation

def mapped_rmsd(moving, fixed, maps):
    """Minimize over chemistry-approved atom maps in an ALREADY aligned receptor frame.

    Do not align the ligand independently: doing so erases the pose error.
    Each map gives the moving atom index for each fixed atom index.
    """
    moving, fixed = xyz(moving), xyz(fixed)
    if moving.shape != fixed.shape or not len(moving):
        raise ValueError('Ligand atom counts disagree or are empty')
    best = float('inf')
    for mapping in maps:
        mapping = np.asarray(mapping)
        if len(mapping) != len(fixed) or sorted(mapping.tolist()) != list(range(len(moving))):
            raise ValueError('Atom map is not a bijection')
        best = min(best, float(np.sqrt(np.mean(np.sum((moving[mapping]-fixed)**2,axis=1)))))
    if not np.isfinite(best):
        raise ValueError('No valid chemical atom maps')
    return best

def residue_contacts(protein, residue_ids, ligand, cutoff):
    protein, ligand = xyz(protein), xyz(ligand)
    if len(protein) != len(residue_ids) or not len(ligand) or cutoff <= 0:
        raise ValueError('Invalid contact inputs')
    contacts = set()
    for start in range(0, len(protein), 512):
        distance2 = ((protein[start:start+512,None,:]-ligand[None,:,:])**2).sum(axis=2)
        hit = (distance2 <= cutoff**2).any(axis=1)
        contacts.update(residue_ids[start+i] for i in np.flatnonzero(hit))
    return contacts

def contact_jaccard(first, second):
    first, second = set(first), set(second)
    union = first | second
    # Two empty contact sets do not supply evidence of a shared binding mode.
    return len(first & second)/len(union) if union else None
