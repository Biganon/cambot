with open("grammalecte.txt", "r") as f:
    lines = f.read().splitlines()

lines = lines[16:]

for line in lines:
    (id_, fid, flexion, lemme, etiquettes, metagraphe, metaphone,
     notes, semantique, etymologie, sous_dictionnaire, google_1_grams,
     wikipedia, wikisource, litterature, total, doublons, multiples,
     frequence, indice) = line.split("\t")

    etiquettes = etiquettes.split()
    if "nom" in etiquettes:
        print(flexion)
    elif "adj" in etiquettes:
        print(flexion)
    elif "adv" in etiquettes:
        print(flexion)
    elif "infi" in etiquettes:
        print(flexion)