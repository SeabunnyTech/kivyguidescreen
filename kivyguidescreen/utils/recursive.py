def recursive_round(obj, decimals=2):
    import numpy as np
    if isinstance(obj, float):
        return round(obj, decimals)
    elif isinstance(obj, list):
        return [recursive_round(it, decimals) for it in obj]
    elif isinstance(obj, tuple):
        return tuple(recursive_round(it, decimals) for it in obj)
    elif isinstance(obj, dict):
        return {k: recursive_round(v, decimals) for k, v in obj.items()}
    elif isinstance(obj, np.ndarray):
        return obj.round(decimals)
    else:
        return obj