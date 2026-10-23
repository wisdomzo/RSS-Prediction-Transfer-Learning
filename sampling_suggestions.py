"""Validated, unique-location sampling for Results Explorer."""
import json
import numpy as np
import pandas as pd
import sampling_kernels as kernels

METHODS = {'uras', 'uras_spatial', 'random', 'top_u', 'bottom_u', 'k_center',
           'gp', 'dbscan_nn', 'uras_no_u', 'uras_no_dbscan', 'uras_spatial_no_u'}
UNCERTAINTY_METHODS = {'uras', 'uras_spatial', 'top_u', 'bottom_u', 'uras_no_dbscan'}


def generate_suggestions(records, options):
    method = options.get('method', 'uras')
    if method not in METHODS:
        raise ValueError('Unknown sampling method.')
    df = pd.DataFrame(records)
    if not {'Latitude', 'Longitude'} <= set(df):
        raise ValueError('Latitude and Longitude are required.')
    for col in ('Latitude', 'Longitude'):
        df[col] = pd.to_numeric(df[col], errors='raise')
    if (not np.isfinite(df[['Latitude', 'Longitude']].to_numpy()).all()
            or not df.Latitude.between(-90, 90).all()
            or not df.Longitude.between(-180, 180).all()):
        raise ValueError('Invalid coordinates in prediction results.')
    original_count = len(df)
    df = df.drop_duplicates(['Latitude', 'Longitude'], keep='first').reset_index(drop=True)
    if df.empty:
        raise ValueError('No candidate locations.')
    if method in UNCERTAINTY_METHODS:
        if 'Uncertainty' not in df:
            raise ValueError('This method requires an Uncertainty column.')
        df['Uncertainty'] = pd.to_numeric(df.Uncertainty, errors='raise')
        if not np.isfinite(df.Uncertainty).all() or (df.Uncertainty < 0).any():
            raise ValueError('Uncertainty must be finite and nonnegative.')
    # Internal identity is independent of user-supplied SampleID type or duplicates.
    original_ids = df['SampleID'].copy() if 'SampleID' in df else None
    df['SampleID'] = np.arange(len(df))
    value = float(options.get('budget', 10))
    mode = options.get('budget_mode', 'percent')
    if not np.isfinite(value) or value <= 0 or mode not in {'percent', 'count'}:
        raise ValueError('Invalid sampling budget.')
    if mode == 'percent' and value > 100:
        raise ValueError('Percentage must not exceed 100.')
    if mode == 'count' and not value.is_integer():
        raise ValueError('Point count must be an integer.')
    budget = int(np.floor(len(df) * value / 100)) if mode == 'percent' else int(value)
    if not 1 <= budget <= len(df):
        raise ValueError(f'Budget must select between 1 and {len(df)} unique locations.')
    eps = float(options.get('eps', .0008))
    min_samples = float(options.get('min_samples', 20))
    seed = float(options.get('seed', 42))
    spacing = float(options.get('initial_spacing', 30))
    scale = float(options.get('gp_scale', 100))
    if not np.isfinite([eps, min_samples, seed, scale]).all() or eps <= 0 or min_samples < 1 or not min_samples.is_integer() or not seed.is_integer() or not 0 <= seed < 2**32 or scale <= 0:
        raise ValueError('Invalid advanced sampling parameters.')
    kernels.spacing_schedule(spacing)
    min_samples, seed = int(min_samples), int(seed)
    metadata = {}
    if method == 'random':
        selected = df.sample(n=budget, random_state=seed)
    elif method in {'top_u', 'bottom_u'}:
        ordered = df.sort_values('Uncertainty', ascending=False, kind='stable')
        selected = ordered.head(budget) if method == 'top_u' else ordered.tail(budget)
    elif method == 'uras':
        selected = kernels.sample_uras(df, kernels.uras_regions(df, eps, min_samples), budget)
    elif method == 'uras_no_dbscan':
        selected, metadata = kernels.sample_uras_no_dbscan(df, budget)
    elif method == 'uras_spatial':
        selected, metadata = kernels.sample_spatial(df, budget, eps, min_samples, spacing)
    elif method in {'uras_no_u', 'uras_spatial_no_u'}:
        selected, metadata = kernels.sample_no_u(df, budget, eps, min_samples, method.endswith('spatial_no_u'), spacing)
    elif method in {'k_center', 'gp'}:
        positions, _ = kernels.spatial_coordinates(df)
        if method == 'gp':
            # Repeated GP fitting is cubic in budget; protect the interactive app.
            if budget > 500 or len(df) > 20000:
                raise ValueError('Spatial GP supports up to 20,000 candidates and 500 selected points.')
            indices, metadata = kernels.sample_gp(positions, budget, seed, scale)
        else:
            indices = kernels.sample_k_center(positions, budget, seed)
        selected = df.iloc[indices].copy()
    else:
        lat, lon = float(options.get('start_lat', 'nan')), float(options.get('start_lon', 'nan'))
        selected, metadata = kernels.sample_dbscan_nn(df, budget, lat, lon, eps, min_samples)
    selected = selected.copy()
    if original_ids is not None:
        selected['SampleID'] = original_ids.iloc[selected.SampleID.to_numpy(dtype=int)].to_numpy()
    selected['Sampling_Order'] = np.arange(1, len(selected) + 1)
    selected['Sampling_Method'] = method
    rounds = metadata.get('rounds', [])
    return {'records': json.loads(selected.to_json(orient='records')),
            'method': method, 'candidate_count': len(df), 'removed_duplicates': original_count-len(df),
            'selected_count': len(selected), 'rounds': rounds}
