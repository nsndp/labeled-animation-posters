# converting WIDER dataset labels from their format to our format

def wider(src):
    out = []
    with open(src, 'r', encoding='utf-8') as f:
        fn = f.readline().rstrip()
        while fn:
            c = int(f.readline().rstrip())
            if c == 0:
                f.readline() # skipping "0 0 0 0 0 0 0 0 0 0" line
                dat = '-'
            else:
                dat = []
                for i in range(c):
                    box = [int(el) for el in f.readline().split(' ')[:4]]
                    box[2] += box[0] # xywh -> x1y1x2y2
                    box[3] += box[1] # xywh -> x1y1x2y2
                    dat.append(' '.join([str(el) for el in box]))
                dat = ', '.join(dat)
            out.append(fn + ': ' + dat)
            fn = f.readline().rstrip()
    return sorted(out, key=str.casefold)

def write(lines, pt):
    with open(pt, 'w', encoding='utf-8') as f:
        for ln in lines:
            f.write(ln + '\n')

if __name__ == '__main__':
    lines = wider('D:/Data/WIDER/wider_face_split/wider_face_train_bbx_gt.txt')
    write(lines, 'D:/Data/WIDER/WIDER_train/labels.txt')
    #from utils import list_files
    #files = list_files('D:/Data/WIDER/WIDER_train/images')