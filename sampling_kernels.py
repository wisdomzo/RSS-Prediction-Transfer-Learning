"""Sampling kernels adapted from IEEE_TCCN_ASSET/Comments/code (October 2026).

Only selection functions are included; experiment runners and file writers are excluded.
"""
from math import radians, sin, cos, atan2, sqrt
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel

FEATURES = ['Latitude', 'Longitude']
LAYERS = ['high', 'middle', 'low']


def spacing_schedule(initial):
    """Decrease by 10 m; below 10 m use unrestricted filling."""
    if not np.isfinite(initial) or initial < 0 or initial > 10000:
        raise ValueError("Initial spacing must be between 0 and 10000 m.")
    rounds = []
    while initial >= 10:
        rounds.append(float(initial))
        initial -= 10
    return rounds + [None]


def spatial_coordinates(df):
    """Local equirectangular approximation in meters, suitable for the Nago extent."""
    origin = df[FEATURES].mean().to_numpy()
    radius = 6371008.8
    angles = np.deg2rad(df[FEATURES].to_numpy()-origin)
    east = radius*np.cos(np.deg2rad(origin[0]))*angles[:, 1]
    north = radius*angles[:, 0]
    return np.column_stack([east, north]), {
        'projection': 'local equirectangular approximation', 'units': 'meters',
        'origin_latitude': float(origin[0]), 'origin_longitude': float(origin[1]),
        'earth_radius_m': radius, 'axis_scaling': 'none; physical Euclidean distances'}

def best_region(part, eps, min_samples):
    if part.empty:
        return part
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(part[FEATURES[:2]])
    valid = sorted(set(labels)-{-1})
    if not valid:
        return part
    best = max(valid, key=lambda c: part.loc[labels == c, 'Uncertainty'].mean()
               * np.log1p(np.sum(labels == c)))
    return part.loc[labels == best]

def uras_regions(df, eps, min_samples):
    ordered = df.sort_values('Uncertainty', ascending=False, kind='stable')
    edge = int(len(df)*.2)
    return [best_region(p, eps, min_samples) for p in
            [ordered.iloc[:edge], ordered.iloc[edge:len(df)-edge],
             ordered.iloc[len(df)-edge:]]]

def sample_uras(df, regions, budget):
    """Deterministic URAS: descending uncertainty in EVERY selected region."""
    quotas = [int(budget*.7), int(budget*.2)]
    quotas.append(budget-sum(quotas))
    selected = []
    for region, quota in zip(regions, quotas):
        count = min(quota, len(region))
        rows = region.sort_values('Uncertainty', ascending=False, kind='stable').head(count)
        selected.extend(rows.index)
    remaining = df.loc[~df.index.isin(selected)].sort_values(
        'Uncertainty', ascending=False, kind='stable')
    selected.extend(remaining.head(budget-len(selected)).index)
    return df.loc[selected]

def sample_k_center(x, budget, seed):
    """Spatial farthest-first coverage using only projected positions in meters."""
    selected = [int(np.random.default_rng(seed).integers(len(x)))]
    minimum_distance = np.full(len(x), np.inf)
    for _ in range(budget-1):
        minimum_distance = np.minimum(minimum_distance,
                                      np.sum((x-x[selected[-1]])**2, axis=1))
        minimum_distance[selected] = -np.inf
        selected.append(int(np.argmax(minimum_distance)))
    return selected

def sample_gp(x, budget, seed, length_scale_m=100.):
    """Spatial GP variance-based batch sampling; no labels or committee outputs."""
    if length_scale_m <= 0 or not np.isfinite(length_scale_m):
        raise ValueError('GP length scale must be finite and positive.')
    initial = min(budget, max(5, int(budget*.1)))
    selected = list(np.random.default_rng(seed).choice(len(x), initial, replace=False))
    kernel = (ConstantKernel(1., 'fixed')*Matern(length_scale_m, 'fixed', nu=1.5)
              + WhiteKernel(.1, 'fixed'))
    while len(selected) < budget:
        # Fixed-kernel posterior variance is independent of target values.
        # Zero placeholders satisfy the sklearn API; prediction means are discarded.
        gp = GaussianProcessRegressor(
            kernel=kernel, alpha=1e-8, normalize_y=False, optimizer=None)
        gp.fit(x[selected], np.zeros(len(selected)))
        remaining = np.setdiff1d(np.arange(len(x)), selected)
        _, std = gp.predict(x[remaining], return_std=True)
        best = int(np.argmax(std))
        p = int(remaining[best])
        selected.append(p)
    return selected, {
        'initial_rows': initial, 'target': None, 'label_free': True,
        'method': 'spatial GP variance-based batch sampling',
        'acquisition': 'greedy maximum conditional variance within one batch, no label feedback',
        'hyperparameters': 'fixed a priori; signal variance 1, noise variance 0.1',
        'length_scale_m': length_scale_m,
        'final_kernel': str(kernel)}

def remaining_test(df, frame, budget):
    """Complement of this method's FT set, retaining original SampleID row identity."""
    database_ids = set(df.SampleID)
    ft_ids = set(frame.SampleID)
    if len(frame) != budget or not frame.SampleID.is_unique or not ft_ids <= database_ids:
        raise ValueError('Invalid FT count or membership.')
    test = df.loc[~df.SampleID.isin(ft_ids)].copy()
    assert ft_ids.isdisjoint(test.SampleID)
    assert ft_ids | set(test.SampleID) == database_ids
    assert len(frame)+len(test) == len(df)
    return test

def sample_spatial(df, budget, eps=.0008, min_samples=20, initial_spacing=30.):
    if not 0 < budget <= len(df):
        raise ValueError('Budget must be between 1 and database size.')
    df = df.reset_index(drop=True)
    # Fixed identity order also makes DBSCAN border-point assignment reproducible.
    identity_order = df.sort_values('SampleID', kind='stable')
    ordered = identity_order.sort_values('Uncertainty', ascending=False, kind='stable')
    edge = int(len(df)*.2)
    parts = [ordered.iloc[:edge], ordered.iloc[edge:len(df)-edge], ordered.iloc[len(df)-edge:]]
    x, projection = spatial_coordinates(identity_order)
    positions = np.empty_like(x)
    positions[identity_order.index.to_numpy()] = x
    groups, clusters, layer_for_row = [], [], {}
    for layer, part in zip(LAYERS, parts):
        layer_for_row.update({int(i): layer for i in part.index})
        fixed = part.sort_values('SampleID', kind='stable')
        labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(fixed[['Latitude', 'Longitude']])
        valid = sorted(set(labels)-{-1})
        ranked = []
        for label in valid:
            region = fixed.loc[labels == label]
            score = float(region.Uncertainty.mean()*np.log1p(len(region)))
            ranked.append((score, region.SampleID.min(), int(label), region))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        layer_groups = []
        for score, _, label, region in ranked:
            rows = region.sort_values(['Uncertainty', 'SampleID'], ascending=[False, True])
            layer_groups.append((f'cluster_{label}', rows.index.tolist()))
            clusters.append({'layer': layer, 'cluster': int(label), 'rows': len(region), 'score': score})
        if valid:
            noise = fixed.loc[labels == -1].sort_values(
                ['Uncertainty', 'SampleID'], ascending=[False, True])
            layer_groups.append(('noise', noise.index.tolist()))
        else:
            rows = fixed.sort_values(['Uncertainty', 'SampleID'], ascending=[False, True])
            layer_groups.append(('whole_layer_fallback', rows.index.tolist()))
        groups.append(layer_groups)

    selected, selected_set, trace = [], set(), []

    def visit(layer_index, target, spacing):
        added = 0
        for group, candidates in groups[layer_index]:
            for idx in candidates:
                if added >= target:
                    return added
                if idx in selected_set:
                    continue
                distance = (float(np.linalg.norm(positions[selected]-positions[idx], axis=1).min())
                            if selected else None)
                # None removes the restriction, allowing distinct rows at one position.
                if spacing is not None and distance is not None and distance <= spacing:
                    continue
                selected.append(idx)
                selected_set.add(idx)
                added += 1
                sample_id = df.at[idx, 'SampleID']
                if isinstance(sample_id, np.generic):
                    sample_id = sample_id.item()
                trace.append({'SampleID': sample_id, 'layer': LAYERS[layer_index],
                              'group': group, 'spacing_m': spacing,
                              'nearest_previous_selected_m': distance})
        return added

    quotas = [int(budget*.7), int(budget*.2)]
    quotas.append(budget-sum(quotas))
    transfers, carry = [], 0
    for i, quota in enumerate(quotas):
        available = quota+carry
        added = visit(i, available, spacing_schedule(initial_spacing)[0])
        transfers.append({'layer': LAYERS[i], 'initial_quota': quota, 'carry_in': carry,
                          'available': available, 'selected': added, 'carry_out': available-added})
        carry = available-added
    rounds = [{'spacing_m': spacing_schedule(initial_spacing)[0], 'added': len(selected), 'total': len(selected)}]
    for spacing in spacing_schedule(initial_spacing)[1:]:
        if len(selected) == budget:
            break
        before = len(selected)
        for i in range(3):
            visit(i, budget-len(selected), spacing)
        rounds.append({'spacing_m': spacing, 'added': len(selected)-before, 'total': len(selected)})
    ft = df.loc[selected].copy()
    remaining_test(df, ft, budget)
    metadata = {
        'method': 'uras_spatial', 'deterministic': True, 'sampling_seed': None,
        'selection_columns': ['Latitude', 'Longitude', 'Uncertainty'],
        'uses_rssi_for_selection': False, 'uncertainty_partitions': [.2, .6, .2],
        'initial_quotas': dict(zip(LAYERS, quotas)),
        'dbscan': {'eps_degrees': eps, 'min_samples': min_samples},
        'cluster_score': 'mean(Uncertainty) * log(1 + row_count)',
        'tie_break': 'SampleID ascending; DBSCAN input also ordered by SampleID',
        'noise_policy': 'After all valid clusters in the same layer; no clusters => whole-layer fallback',
        'transfer_policy': 'Unused initial quota moves high -> middle -> low',
        'relaxation_policy': 'Decrease spacing by 10m; below 10m use unrestricted filling',
        'distance_rule': 'Strictly greater than threshold from ALL previously selected points across all layers',
        'spatial_coordinates': projection, 'clusters': clusters,
        'initial_round_transfers': transfers, 'rounds': rounds,
        'actual_layer_counts': {layer: sum(layer_for_row[i] == layer for i in selected) for layer in LAYERS},
        'unique_ft_locations': len(ft.drop_duplicates(['Latitude', 'Longitude'])),
        'selection_trace': trace,
    }
    return ft, metadata

def sample_no_u(df, budget, eps=.0008, min_samples=20, use_spacing=True, initial_spacing=30.):
    if not 0 < budget <= len(df):
        raise ValueError('Budget must be between 1 and database size.')
    if not df.SampleID.is_unique or df.SampleID.isna().any():
        raise ValueError('SampleID must be unique and non-null.')
    df = df.copy()
    df[FEATURES] = df[FEATURES].apply(pd.to_numeric, errors='raise')
    values = df[FEATURES].to_numpy()
    if (not np.isfinite(values).all() or (np.abs(values[:, 0]) > 90).any()
            or (np.abs(values[:, 1]) > 180).any()):
        raise ValueError('Invalid latitude/longitude.')
    # SampleID only breaks ties between records at the same coordinate.
    df = df.sort_values([*FEATURES, 'SampleID'], kind='stable').reset_index(drop=True)
    positions, projection = spatial_coordinates(df)
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(df[FEATURES])
    valid = sorted(set(labels)-{-1})
    ranked = sorted((np.flatnonzero(labels == k).tolist() for k in valid),
                    key=lambda indices: (-len(indices), indices[0]))
    groups = [(f'cluster_{int(labels[indices[0]])}', indices) for indices in ranked]
    clusters = [{'group': name, 'rows': len(indices), 'score': float(np.log1p(len(indices)))}
                for name, indices in groups]
    noise = np.flatnonzero(labels == -1).tolist()
    if noise:
        groups.append(('noise' if valid else 'whole_pool_fallback', noise))

    selected, selected_set, trace, rounds, transfers = [], set(), [], [], []
    for spacing in (spacing_schedule(initial_spacing) if use_spacing else [None]):
        if len(selected) == budget:
            break
        before = len(selected)
        for group, indices in groups:
            available = budget-len(selected)
            if not available:
                break
            group_before = len(selected)
            for idx in indices:
                if len(selected) == budget:
                    break
                if idx in selected_set:
                    continue
                distance = (float(np.linalg.norm(positions[selected]-positions[idx], axis=1).min())
                            if selected else None)
                if spacing is not None and distance is not None and distance <= spacing:
                    continue
                selected.append(idx)
                selected_set.add(idx)
                sample_id = df.at[idx, 'SampleID']
                trace.append({'SampleID': sample_id.item() if isinstance(sample_id, np.generic) else sample_id,
                              'group': group, 'spacing_m': spacing,
                              'nearest_previous_selected_m': distance})
            transfers.append({'group': group, 'spacing_m': spacing, 'available': available,
                              'selected': len(selected)-group_before, 'remaining': budget-len(selected)})
        rounds.append({'spacing_m': spacing, 'added': len(selected)-before, 'total': len(selected)})
    ft = df.loc[selected].copy()
    remaining_test(df, ft, budget)
    metadata = {
        'method': 'uras_spatial_no_u' if use_spacing else 'uras_no_u', 'deterministic': True, 'sampling_seed': None,
        'selection_columns': FEATURES, 'uses_rssi_for_selection': False,
        'uses_uncertainty_for_selection': False, 'uncertainty_partitions': None,
        'initial_quotas': {'whole_pool': budget},
        'dbscan': {'eps_degrees': eps, 'min_samples': min_samples,
                   'input_order': 'latitude, longitude, SampleID ascending'},
        'cluster_score': 'log(1 + row_count)',
        'within_cluster_order': 'latitude, longitude, SampleID ascending',
        'noise_policy': 'After all valid clusters; no clusters => whole-pool fallback',
        'transfer_policy': 'One shared budget; unused budget passes to the next cluster, then noise',
        'relaxation_policy': 'Decrease spacing by 10m; below 10m use unrestricted filling' if use_spacing else None,
        'distance_rule': 'Strictly greater than threshold from ALL previously selected points' if use_spacing else None,
        'duplicate_policy': ('Rows retain separate SampleIDs, as in URAS-Spatial; unrestricted fallback may select repeated coordinates'
                             if use_spacing else 'Rows retain separate SampleIDs; repeated coordinates may be selected'),
        'spatial_coordinates': projection, 'clusters': clusters, 'noise_rows': len(noise),
        'rounds': rounds, 'budget_transfers': transfers,
        'unique_ft_locations': len(ft.drop_duplicates(FEATURES)),
        'selection_trace': trace,
    }
    return ft, metadata

def sample_uras_no_dbscan(df, budget):
    if not 0 < budget <= len(df):
        raise ValueError('Budget must be between 1 and database size.')
    if not df.SampleID.is_unique or df.SampleID.isna().any():
        raise ValueError('SampleID must be unique and non-null.')
    df = df.reset_index(drop=True).copy()
    df['Uncertainty'] = pd.to_numeric(df.Uncertainty, errors='raise')
    if not np.isfinite(df.Uncertainty).all() or (df.Uncertainty < 0).any():
        raise ValueError('Uncertainty must be finite and nonnegative.')
    ordered = df.sort_values('Uncertainty', ascending=False, kind='stable')
    edge = int(len(df)*.2)
    parts = [ordered.iloc[:edge], ordered.iloc[edge:len(df)-edge], ordered.iloc[len(df)-edge:]]
    # Reuse the exact production URAS quota/refill implementation, with complete strata as regions.
    ft = sample_uras(df, parts, budget)
    remaining_test(df, ft, budget)
    quotas = [int(budget*.7), int(budget*.2)]
    quotas.append(budget-sum(quotas))
    first_ids = set(idx for part, quota in zip(parts, quotas) for idx in part.head(quota).index)
    metadata = {
        'method': 'uras_no_dbscan', 'deterministic': True, 'sampling_seed': None,
        'selection_columns': ['Uncertainty'], 'uses_rssi_for_selection': False,
        'uses_coordinates_for_selection': False, 'uses_uncertainty_for_selection': True,
        'uncertainty_partitions': [.2, .6, .2], 'dbscan': None, 'cluster_score': None,
        'initial_quotas': dict(zip(LAYERS, quotas)),
        'stratum_rows': dict(zip(LAYERS, [len(part) for part in parts])),
        'initial_selected_counts': dict(zip(LAYERS, [min(len(part), q) for part, q in zip(parts, quotas)])),
        'actual_layer_counts': {layer: int(ft.index.isin(part.index).sum()) for layer, part in zip(LAYERS, parts)},
        'within_layer_order': 'Uncertainty descending in all strata',
        'tie_break': 'Stable original database row order, identical to current URAS',
        'shortfall_policy': 'After fixed quotas, fill from all unselected rows by descending Uncertainty',
        'global_refill_rows': int(len(ft)-len(first_ids)),
        'minimum_spacing_m': None, 'relaxation_policy': None, 'route_optimization': False,
        'duplicate_policy': 'Different SampleIDs remain separate rows, including repeated coordinates',
        'unique_ft_locations': len(ft.drop_duplicates(['Latitude', 'Longitude']))
                               if {'Latitude', 'Longitude'} <= set(ft.columns) else None,
        'selected_sample_ids': [x.item() if isinstance(x, np.generic) else x for x in ft.SampleID],
    }
    return ft, metadata

def sample_dbscan_nn(df, budget, start_lat, start_lon, eps=.0008, min_samples=20):
    if not 0 < budget <= len(df):
        raise ValueError('Budget must be between 1 and database size.')
    if not df.SampleID.is_unique or df.SampleID.isna().any():
        raise ValueError('SampleID must be unique and non-null.')
    values = df[FEATURES].to_numpy(dtype=float)
    if (not np.isfinite(values).all() or (np.abs(values[:, 0]) > 90).any()
            or (np.abs(values[:, 1]) > 180).any()
            or not np.isfinite([start_lat, start_lon]).all()
            or abs(start_lat) > 90 or abs(start_lon) > 180):
        raise ValueError('Invalid latitude/longitude.')
    # Coordinates alone decide locations; lowest SampleID maps a repeated location to one source row.
    unique = df.sort_values('SampleID', kind='stable').drop_duplicates(FEATURES)
    unique = unique.sort_values(FEATURES, kind='stable').reset_index(drop=True)
    if len(unique) < budget:
        raise ValueError(f'Only {len(unique)} distinct locations for budget {budget}.')
    points = list(zip(unique.Latitude, unique.Longitude))
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(unique[FEATURES])
    clusters = {int(k): np.flatnonzero(labels == k).tolist() for k in sorted(set(labels)-{-1})}
    noise = np.flatnonzero(labels == -1).tolist()

    def distance(position, idx):
        return calculate_travel_distance([points[idx]], *position)

    def walk(indices, position, count):
        remaining = list(indices)
        route, length = [], 0.
        while remaining and len(route) < count:
            # Indices follow lexicographic coordinates, so equal-distance ties are deterministic.
            best = min(remaining, key=lambda idx: (distance(position, idx), idx))
            length += distance(position, best)
            route.append(best)
            remaining.remove(best)
            position = points[best]
        return route, length, position

    start = (start_lat, start_lon)
    eligible = {k: ids for k, ids in clusters.items() if len(ids) >= budget}
    candidates = []
    if eligible:
        for k, ids in eligible.items():
            route, length, _ = walk(ids, start, budget)
            candidates.append((length, route, k))
        length, selected, winner = min(candidates, key=lambda item: (item[0], item[1]))
        visits = [winner]
        policy = 'shortest eligible single-cluster nearest-neighbor route'
    else:
        selected, visits, length, current = [], [], 0., start
        remaining_clusters = dict(clusters)
        while remaining_clusters and len(selected) < budget:
            winner = min(remaining_clusters,
                         key=lambda k: min((distance(current, idx), idx) for idx in remaining_clusters[k]))
            route, part_length, current = walk(remaining_clusters.pop(winner), current, budget-len(selected))
            selected.extend(route)
            visits.append(winner)
            length += part_length
        if len(selected) < budget:
            route, part_length, current = walk(noise, current, budget-len(selected))
            selected.extend(route)
            length += part_length
            visits.append('noise')
        policy = 'nearest-entry clusters, then noise; all-noise case uses global nearest neighbors'
    assert len(selected) == budget and len(set(selected)) == budget
    ft = unique.iloc[selected].copy()
    metadata = {
        'method': 'dbscan_nn', 'deterministic': True, 'sampling_seed': None,
        'selection_columns': FEATURES, 'uses_rssi_for_selection': False,
        'uses_uncertainty_for_selection': False, 'minimum_spacing_m': None,
        'start_latitude': start_lat, 'start_longitude': start_lon, 'return_leg': False,
        'dbscan': {'eps_degrees': eps, 'min_samples': min_samples,
                   'input_order': 'latitude, longitude ascending; unique coordinates'},
        'duplicate_policy': 'One location per exact coordinate pair; lowest SampleID source row represents it',
        'tie_break': 'Lexicographic latitude/longitude; equal route lengths use coordinate-sequence order',
        'distinct_candidate_locations': len(unique), 'unique_ft_locations': len(ft),
        'clusters': [{'cluster': k, 'distinct_locations': len(ids)} for k, ids in clusters.items()],
        'noise_locations': len(noise), 'policy': policy, 'cluster_visit_order': visits,
        'candidate_routes': [{'cluster': k, 'length_km': value} for value, _, k in candidates],
        'acquisition_route_km': length,
        'evaluation_route_km': calculate_travel_distance(list(zip(ft.Latitude, ft.Longitude)), *start),
        'evaluation_route_rule': 'Common global nearest-neighbor estimator on final FT positions; no return',
        'selected_sample_ids': [x.item() if isinstance(x, np.generic) else x for x in ft.SampleID],
        'test_duplicate_policy': 'Only selected SampleIDs removed; other rows at selected coordinates remain in test',
    }
    return ft, metadata

def calculate_travel_distance(points, start_lat, start_lon):
    """Nearest-neighbor great-circle route in km, starting at Tx without return."""
    def haversine(lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
        dlat, dlon = lat2-lat1, lon2-lon1
        a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
        return 6371.0*(2*atan2(sqrt(a), sqrt(1-a)))

    unvisited = list(points)
    current_lat, current_lon = start_lat, start_lon
    total_distance = 0.
    while unvisited:
        distances = [haversine(current_lat, current_lon, p[0], p[1]) for p in unvisited]
        idx = np.argmin(distances)
        total_distance += distances[idx]
        current_lat, current_lon = unvisited.pop(idx)
    return total_distance

