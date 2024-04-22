import os.path as osp
import time
import tkinter as tk
import PIL.Image, PIL.ImageTk


class DelCandidatesChecker():

    def __init__(self, maximized=False, window_size=(1280,720), delay=1):
        #self.root = tk.Toplevel()
        #if self.root is None:
        #    self.root = tk.Tk()
        self.root = tk.Tk()
        if maximized:
            self.root.state('zoomed')
        else:
            w, h = window_size
            sw = self.root.winfo_screenwidth()
            self.root.geometry('%sx%s+%s+%s' % (w, h, (sw - w) // 2, 50))
        self.labels = [None] * 2
        self.images = [None] * 2
        for i in range(2):
            self.labels[i] = tk.Label(self.root, font=('Arial', 18))
            self.labels[i].place(relx=i*0.5+0.25, rely=0.05, anchor='center')
            f = tk.Frame(self.root, bg='#dddddd')
            f.place(relx=i*0.5, rely=0.1, relwidth=0.5, relheight=0.9)
            self.images[i] = tk.Label(f)
            self.images[i].place(relx=0.5, rely=0.5, anchor='center')
            self.root.update()
            self.frame_size = (f.winfo_width(), f.winfo_height())
        self.notice = tk.Label(self.root, font=('Arial', 25))
        self.notice.place(relx=0.5, rely=0.04, anchor='center')
        self.root.bind('<space>', lambda event: self.key_press(event, 'YES'))
        self.root.bind('r', lambda event: self.key_press(event, 'NO'))
        self.root.bind('s', lambda event: self.key_press(event, 'SWAP'))
        self.root.bind('<BackSpace>', lambda event: self.key_press(event, 'BACK'))
        self.root.bind('<Shift-E>', lambda e: self.root.quit())
        self.delay = delay

    def load_pair(self):
        if self.k >= len(self.data):
            self.root.quit()
            return
        self.cur_pair = self.data[self.k]
        val = self.cur_pair[-1]
        val = str(val) if isinstance(val, int) else '%.4f' % val
        self.notice.config(text=val, fg='black')
        self.root.title('%d out of %d' % (self.k + 1, len(self.data)))
        for i, fn in enumerate(self.cur_pair[:2]):
            path = osp.join(self.updir, fn)
            text = 'TO KEEP' if i == 0 else 'TO REMOVE'
            im = PIL.Image.open(path)
            kb = round(osp.getsize(path) / 1024)
            info = '%s\n%s\n%s x %s (%d Kb)' % (text, fn, *im.size, kb)
            im.thumbnail(self.frame_size)
            img = PIL.ImageTk.PhotoImage(im)
            self.labels[i].config(text=info)
            self.images[i].config(image=img)
            self.images[i].photo = img
    
    def key_press(self, e, choice):
        if choice == 'BACK':
            if self.k >= 1:
                ch = -1
                while ch == -1 and self.k > 0:
                    self.k -= 1
                    ch = self.choices.pop()
                self.load_pair()
            return
        if choice == 'NO':
            self.notice.config(text='CANCELED', fg='red')
            self.choices.append(0)
        elif choice == 'YES':
            self.notice.config(text='APPROVED', fg='green')
            self.choices.append(self.cur_pair[1])
        elif choice == 'SWAP':
            self.notice.config(text='SWAPPED + APPROVED', fg='blue')
            self.choices.append(self.cur_pair[0])
        if self.delay:
            self.root.update()
            time.sleep(self.delay)
        self.make_step()
        self.load_pair()
        
    def make_step(self):
        self.k += 1
        skip = True
        while skip and self.k < len(self.data):
            p = self.data[self.k][:2]
            if p[0] in self.choices or p[1] in self.choices:
                self.choices.append(-1)
                self.k += 1
            else:
                skip = False
    
    def __call__(self, updir, data):
        self.updir = updir
        self.data = data
        self.choices = []
        self.k = 0
        self.load_pair()
        self.root.mainloop()
        return self.choices