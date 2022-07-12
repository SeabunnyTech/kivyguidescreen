import numpy as np


def renumpy(obj):

    if isinstance(obj, list):
        return [renumpy(e) for e in obj]

    if isinstance(obj, dict):
        if 'isnumpy' in obj:
            # 這個 dict 是 numpy 要組回來
            return np.load(obj['path'])
        else:
            return {k:renumpy(v) for k, v in obj.items()}

    return obj


def denumpy(obj, var_key=None):
    # 這個函數會深入 dict 與 list 形成的結構
    # 然後把 numpy 都另存成檔案，再留下檔名
    # 讓 output 物件變得 JSON serializable

    if isinstance(obj, np.ndarray):
        assert var_key is not None
        np.save(var_key, obj)
        return dict(isnumpy=True, path=var_key+'.npy')

    if isinstance(obj, list):
        return [denumpy(e) for e in obj]

    if isinstance(obj, dict):
        return {k:denumpy(v, k) for k, v in obj.items()}

    return obj