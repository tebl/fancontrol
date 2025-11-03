

def to_keypair_str(key, value):
    return str(key) + " (" + str(value) + ")"


def remap_int(value, in_min, in_max, out_min, out_max):
    return out_min + (float(value - in_min) / float(in_max - in_min)) * (out_max - out_min)
