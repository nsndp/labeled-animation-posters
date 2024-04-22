# a simple helper for counting the number of faces inside a labels file

def count_faces(pt, segment=None):
    with open(pt, 'r', encoding='utf-8') as f:
        i = 0
        c = 0
        for line in f:
            i += 1
            if not segment or i >= segment[0] and i <= segment[1]:
                c += len(line.rstrip().split(': ')[1].split(', '))
    return c

if __name__ == "__main__":
    refined = count_faces('D:/Data/LAP/anime/labels_faces.txt', (1, 2000))
    baseline = count_faces('D:/Data/LAP/anime/labels_faces_baseline.txt', (2001, 45286))
    print(refined + baseline)