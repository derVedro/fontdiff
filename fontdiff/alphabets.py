latin_up     = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
latin_low    = "abcdefghijklmnopqrstuvwxyz"
latin        = "".join(cap + low for cap, low in zip(latin_up, latin_low))
cyrillic_up  = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
cyrillic_low = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
cyrillic     = "".join(cap + low for cap, low in zip(cyrillic_up, cyrillic_low))
greek_up     = "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"
greek_low    = "αβγδεζηθικλμνξοπρστυφχψω"
greek        = "".join(cap + low for cap, low in zip(greek_up, greek_low))
numerals     = "0123456789"
symbols      = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"