"""Matriz literal de perfiles de aplicación del bundle: única fuente de expectativas de las pruebas de Python y PowerShell.

Valores escritos a mano desde los perfiles revisados (9–13 y la candidata 14). No se calculan con el producto,
para que una regresión en la tabla del producto no pueda justificarse a sí misma.
Columnas: digest del manifiesto, nombre, esquema de versión, servidor, frontend y bytes de distribución.
"""

MATRIX = (
    ("b7b26834ac5186792a01014b7221f4ba94940da19efafb84546ca635f868fa00", "337", 9, 18, 18, 6578061),
    ("cf51b03c80ddec460944295daf09705f3dbdec0cd83e054f5bfc6592fb081685", "397", 9, 18, 18, 6653702),
    ("c818294e27a40c94fe2ebf603709c94263820af1facca9a7d5c288cb70e8158e", "532", 9, 18, 18, 6794984),
    ("66426b3c4fdf8c75b8c1faae4572066754934000eb2567881d93407f4ae5e9f9", "592", 10, 19, 18, 6939574),
    ("f256c0fc5c99c4ff24c05e36a7eddc0ed2da9d66979db3502e0c4d606ac881cd", "712", 11, 20, 18, 7028507),
    ("511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5", "832", 11, 20, 18, 7108267),
    ("1b40f9ceffde0503c024f0dce1fb79de02c05a21bc9cb93ad3b0d6a3d359dc09", "849", 11, 20, 18, 7108622),
    ("b589609154fed1567106ef0865972155258f0f5474128c73076f4697d43b8bda", "969", 12, 21, 18, 7037914),
    ("c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c", "1089", 13, 22, 18, 7133395),
    ("dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b", "1209", 13, 22, 18, 7146303),
    ("38bbae727ffd545436506ab65d1c66525a64bf316e0a9354079cace0aa60c6b6", "1329", 13, 22, 18, 7148383),
    ("55bdd496ec654494fd8e3400140e3e84241488986e24481939bad67cde7a91c6", "1449", 13, 22, 18, 7159235),
    ("2ec9105661db0f5c9a97d58e2a7f44e69bfd7e1903493b72f0fc57cc94c4b71a", "14", 14, 24, 18, 7263552),
    ("e9c58c0c67500afc09c1ac979a7433830c96f94c2a2e4501d81286796d65d74d", "14", 14, 24, 18, 7489372),
)
# Los doce perfiles anteriores (9–13) conservan sus datos. Los dos del esquema 14 son la candidata M3 congelada y la corregida (D14-05).
HISTORICAL = MATRIX[:-2]
FROZEN_14, CORRECTED_14 = MATRIX[-2], MATRIX[-1]
NEW = FROZEN_14
