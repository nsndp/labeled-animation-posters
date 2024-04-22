import os.path as osp
import tkinter as tk
import PIL.Image, PIL.ImageTk


class GroupExplorer():

    def __init__(self, x=300, y=400, n=6, lbsz=32, max_=30):
        self.root = tk.Tk()
        self.n = n
        self.x = x
        self.y = y
        self.lbsz = lbsz
        self.max_ = max_
        self.initials = {'x': x, 'y': y, 'n': n}
        self.frames = [tk.Frame(self.root) for _ in range(max_)]
        self.canvas = [tk.Label(self.frames[i], borderwidth=0) for i in range(max_)]
        self.labels = [tk.Label(self.frames[i], borderwidth=0) for i in range(max_)]
        self.def_bg = self.labels[0].cget('bg')
        for i in range(max_):
            self.canvas[i].place(relx=0.5, y=self.lbsz, anchor='n')
            self.labels[i].place(relx=0.5, height=self.lbsz, anchor='n')
            self.canvas[i].bind('<1>', lambda e, i=i: self.click(e, i))
        self.root.bind('<3>', self.confirm)
        self.root.bind('<space>', self.confirm)
        self.root.bind('<BackSpace>', self.back)
        self.root.bind('<Key>', self.key_press)
        self.root.bind('<Left>', lambda e: self.key_press(e, 'left'))
        self.root.bind('<Right>', lambda e: self.key_press(e, 'right'))
        self.root.bind('<Up>', lambda e: self.key_press(e, 'up'))
        self.root.bind('<Down>', lambda e: self.key_press(e, 'down'))
        self.root.bind('<MouseWheel>', lambda e: self.key_press(e, 'wheel'))
        # list of all events: https://stackoverflow.com/a/32289245
    
    def init_data(self, updir, groups):
        self.updir = updir
        self.groups = groups
        self.k = 0
        self.choices = []
        self.load_group()
        
    def load_group(self):
        if self.k >= len(self.groups):
            self.root.quit()
            return
        fnames = self.groups[self.k]
        images = [PIL.Image.open(osp.join(self.updir, fn)) for fn in fnames]
        iareas = [im.size[0] * im.size[1] for im in images]
        kbytes = [round(osp.getsize(osp.join(self.updir, fn)) / 1024) for fn in fnames]
        srtidx = [i for i, v in sorted(enumerate(zip(iareas, kbytes)), key=lambda x: (x[1][0], x[1][1]), reverse=True)]
        images = [images[i] for i in srtidx]
        fnames = [fnames[i] for i in srtidx]
        kbytes = [kbytes[i] for i in srtidx]
        for i in range(len(fnames)):
            info = '%s\n%s x %s (%d Kb)' % (fnames[i], *images[i].size, kbytes[i])
            self.labels[i].config(text=info, bg=self.def_bg)
        for i in range(len(fnames), self.max_):
            self.frames[i].grid_forget()
        self.root.title('%d out of %d' % (self.k + 1, len(self.groups)))
        self.fnames = fnames
        self.images = images
        self.candidates = [0] * len(fnames)
        self.update_layout()
    
    def update_layout(self):
        for i, orig in enumerate(self.images):
            self.frames[i].config(width=self.x, height=self.y)
            self.frames[i].grid(row=i//self.n, column=i%self.n, padx=4, pady=4)
            im = orig.copy()
            im.thumbnail((self.x, self.y - self.lbsz))
            img = PIL.ImageTk.PhotoImage(im)
            self.canvas[i].config(image=img)
            self.canvas[i].photo = img
    
    def confirm(self, e):
        sel = [self.fnames[i] for i, v in enumerate(self.candidates) if v == 1]
        self.choices.append(sel)
        self.k += 1
        self.load_group()
        
    def back(self, e):
        if self.k == 0:
            return
        self.k -= 1
        self.load_group()
        last = self.choices.pop()
        for fn in last:
            if fn in self.fnames:
                self.click(None, self.fnames.index(fn))
    
    def click(self, e, i):
        self.labels[i].config(bg='#ff4444' if self.candidates[i] == 0 else self.def_bg)
        self.candidates[i] = 1 if self.candidates[i] == 0 else 0
    
    def key_press(self, e, special=None):
        if e.char in [str(d) for d in range(1, 10)]:
            i = int(e.char) - 1
            if i < len(self.candidates):
                self.click(None, i)
            return
        if e.char == '-' or special == 'left' or special == 'wheel' and e.delta < 0:
            self.x -= 20
        if e.char == '=' or special == 'right' or special == 'wheel' and e.delta > 0:
            self.x += 20
        if e.char == '-' or special == 'up' or special == 'wheel' and e.delta < 0:
            self.y -= 20
        if e.char == '=' or special == 'down' or special == 'wheel' and e.delta > 0:
            self.y += 20
        if e.char == '0':
            self.x = self.initials['x']
            self.y = self.initials['y']
            self.n = self.initials['n']
        if e.char == 'q' and self.n > 1:
            self.n -= 1
        if e.char == 'e' and self.n < 10:
            self.n += 1
        self.update_layout()
        
    def run(self):
        self.root.mainloop()
        return [fn for grp in self.choices for fn in grp]