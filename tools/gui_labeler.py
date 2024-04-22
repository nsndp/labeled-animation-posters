from datetime import datetime
import os
import os.path as osp
import shutil
import tkinter as tk
import PIL.Image, PIL.ImageTk

# drawing on canvas: https://anzeljg.github.io/rin2/book2/2405/docs/tkinter/canvas.html
# list of all events: https://stackoverflow.com/a/32289245

class LabelerGUI():

    colors = ['#FF5500', '#55FF55', '#0099FF', '#FFFFFF', '#000000']
    indic1, indic2 = 'red', 'white'
    mode = ''
    help_text = 'TBD\n' \
                'TBD'
    def_status = 'Use SPACE/BackSpace to change images, Q/E to change pages, ' \
                 'DEL to mark/unmark image for deletion, L to change layout'
    edit_status = 'Use WASD to precisely move the selected corner of the box, ' \
                  'SPACE to finish editing, DELETE to remove the box'

    def __init__(self, maximized=False, window_size=(1600,900), thumb_size=(120,150)):
        # window and its size
        self.root = tk.Tk()
        self.root.minsize(800, 600)
        self.screen_size = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        if maximized:
            self.root.state('zoomed')
            self.root.update()
            self.window_size = (self.root.winfo_width(), self.root.winfo_height())
        else:
            w, h = window_size
            self.window_size = window_size
            self.root.geometry('%sx%s+%s+%s' % (w, h, (self.screen_size[0] - w) // 2, 50))

        # main layout
        self.head = tk.Frame(self.root, bg='#AAAAFF', height=30)
        self.foot = tk.Frame(self.root, bg='#FFAAAA', height=30)
        self.main = tk.Frame(self.root)
        self.head.pack(fill='x', side='top')
        self.foot.pack(fill='x', side='bottom')
        self.nav_init(thumb_size)
        self.main.pack(fill='both', expand=True)
        
        # upper and lower status bars
        self.header = tk.Label(self.head, font=('TkDefaultFont', 12), bg='#AAAAFF')
        self.status = tk.Label(self.foot, font=('TkDefaultFont', 12), bg='#FFAAAA')
        self.header.pack(fill='both', expand=True)
        self.status.pack(fill='both', expand=True)
        self.help = tk.Label(self.head, text='HELP', bg='#AAFFAA', font='TkDefaultFont 10 bold', bd=0)
        self.help.place(x=0, y=0, height=24)
        self.status.config(text=self.def_status)
        
        # canvas with image
        self.canvas = tk.Canvas(self.main, highlightthickness=0, bg='#F0F0F0')
        self.vbar = tk.Scrollbar(self.main, orient='vertical')
        self.hbar = tk.Scrollbar(self.main, orient='horizontal')
        self.vbar.pack(fill='y', side='right')
        self.hbar.pack(fill='x', side='bottom')
        self.vbar.config(command=self.canvas.yview)
        self.hbar.config(command=self.canvas.xview)
        self.canvas.config(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)
        self.canvas.config(xscrollincrement='1', yscrollincrement='1')
        self.root.update()
        self.vbar_size = self.vbar.winfo_width()
        self.hbar_size = self.hbar.winfo_height()
        self.area_size = (self.main.winfo_width(), self.main.winfo_height())
        
        # overlay for delete candidates to hide the image with minimum effort
        self.overlay = tk.Frame(self.main, bg='grey')
        self.overlay_text = tk.Label(self.overlay, text='MARKED FOR DELETION', bg='grey', font='TkDefaultFont 25 bold')
        self.overlay_text.place(relx=.5, rely=.5, anchor='center')
        
        # event bindings
        self.canvas.bind('<ButtonPress-1>', self.click1)
        self.canvas.bind('<ButtonPress-3>', self.click2)
        self.canvas.bind('<ButtonRelease-1>', self.release1)
        self.canvas.bind('<B1-Motion>', self.move1)
        self.canvas.bind('<B3-Motion>', self.move2)
        self.canvas.bind('<MouseWheel>', self.zoom)
        self.help.bind('<ButtonPress-1>', self.show_help)
        self.main.bind('<Configure>', self.area_resize)
        self.root.bind('<space>', self.key_space)
        self.root.bind('<BackSpace>', self.key_back)
        self.root.bind('<Delete>', self.key_del)
        self.root.bind('<Tab>', self.key_tab)
        self.root.bind('<Control-s>', self.save)
        self.root.bind('l', self.nav_change)
        self.root.bind('e', self.next_page)
        self.root.bind('q', self.prev_page)
        self.root.bind('w', lambda e: self.key_move(e, 'up', step=5))
        self.root.bind('a', lambda e: self.key_move(e, 'left', step=5))
        self.root.bind('s', lambda e: self.key_move(e, 'down', step=5))
        self.root.bind('d', lambda e: self.key_move(e, 'right', step=5))
        self.root.bind('<Shift-W>', lambda e: self.key_move(e, 'up', step=2))
        self.root.bind('<Shift-A>', lambda e: self.key_move(e, 'left', step=2))
        self.root.bind('<Shift-S>', lambda e: self.key_move(e, 'down', step=2))
        self.root.bind('<Shift-D>', lambda e: self.key_move(e, 'right', step=2))
        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)
        self.root.bind('c', self.change_color)
        self.root.bind('h', self.toggle_classes)
        for i, c in enumerate([str(d) for d in range(1, 10)] + ['0', '-', '=', '+', '_', ']']):
            self.root.bind(c, lambda e, i=i: self.key_class(e, i + 1))
        self.cli = 0
        self.hide_classes = False

    def nav_init(self, tsz):
        self.nav = tk.Frame(self.root, bg='#CCCCCC')
        self.nav_max = max(self.screen_size[0] // tsz[0], self.screen_size[1] // tsz[1] * 4)
        self.thumb_size = tsz
        self.navbkg = [None] * self.nav_max
        self.thumbs = [None] * self.nav_max
        self.overlays = [None] * self.nav_max
        for i in range(self.nav_max):
            self.navbkg[i] = tk.Frame(self.nav, width=tsz[0], height=tsz[1], bg='#CCCCCC')
            self.thumbs[i] = tk.Label(self.navbkg[i], borderwidth=0, bg='red', fg='red', 
                                      font='TkDefaultFont 18 bold', compound='center') #for TO DEL text
            self.thumbs[i].bind('<1>', lambda e, i=i: self.nav_click(e, i))
        self.nav_state = 3
        self.nav_place()
    
    def nav_calc_n(self):
        if self.nav_state == 0:
            return self.window_size[0] // self.thumb_size[0]
        else:
            b1, b2 = self.head.cget('height'), self.foot.cget('height')
            col_max = (self.window_size[1] - b1 - b2) // self.thumb_size[1]
            return col_max * self.nav_state
    
    def nav_place(self):
        if self.nav_state == 0:
            self.nav.config(height=self.thumb_size[1])
            self.nav.pack(fill='x', side='bottom')
        else:
            self.nav.config(width=self.thumb_size[0] * self.nav_state)
            self.nav.pack(fill='y', side='right')
        self.nav_n = self.nav_calc_n()
        r, c = 0, 0
        for i in range(self.nav_n):
            if self.nav_state == 0:
                self.navbkg[i].grid(row=0, column=i)
            else:
                self.navbkg[i].grid(row=r, column=c)
                c += 1
                if c >= self.nav_state: c = 0; r += 1
            self.thumbs[i].place(relx=0.5, rely=0.5, anchor='center')
        for i in range(self.nav_n, self.nav_max):
            self.navbkg[i].grid_forget()

    def nav_change(self, e):
        self.nav_state += 1
        if self.nav_state > 4:
            self.nav_state = 0
        self.nav_place()
        self.update_page()
        
    def nav_click(self, e, i):
        self.update_selection(i)
        
    def update_page(self, sel_last=False):
        if self.s + self.nav_n > len(self.files):
            # in case we go overboard while changing layout to a bigger one
            self.s = len(self.files) - self.nav_n
        for i, f in enumerate(self.files[self.s:self.s+self.nav_n]):
            im = PIL.Image.open(osp.join(self.updir, f))
            im.thumbnail((self.thumb_size[0] - 6, self.thumb_size[1] - 6)) # 3px of padding on each side
            img = PIL.ImageTk.PhotoImage(im)
            self.thumbs[i].config(image=img)
            self.thumbs[i].photo = img
            self.thumbs[i].config(text='TO DEL' if self.delcands[self.s+i] else '')
        self.k = 0 if not sel_last else self.nav_n - 1
        self.update_selection()
        
    def update_selection(self, i=None):
        if i is not None:
            self.k = i
        if hasattr(self, 'nav_sel'):
            self.thumbs[self.nav_sel].config(borderwidth=0)
        self.thumbs[self.k].config(borderwidth=3)
        self.nav_sel = self.k
        
        fn = self.files[self.s + self.k]
        self.orig = PIL.Image.open(osp.join(self.updir, fn))
        self.img = self.orig.copy()
        self.photo = PIL.ImageTk.PhotoImage(self.img)
        self.rids = []
        
        # initial scale is to fit the area
        self.scale = min(self.area_size[0] / self.img.size[0], self.area_size[1] / self.img.size[1])
        nw = int(self.orig.size[0] * self.scale)
        nh = int(self.orig.size[1] * self.scale)
        self.img = self.orig.resize((nw, nh))
        self.photo = PIL.ImageTk.PhotoImage(self.img)
        self.update_canvas()
        
        inf = (self.files[self.s+self.k], self.s+self.k+1, round(self.scale * 100),
               self.s+1, self.s+self.nav_n, len(self.files))
        self.header.configure(text='%s (#%d) (zoom %d%%) (showing %d-%d out of %d)' % inf)
        
    def next_page(self, e):
        self.s = min(self.s + self.nav_n, len(self.files) - self.nav_n)
        self.update_page()
    
    def prev_page(self, e, sel_last=False):
        self.s = max(0, self.s - self.nav_n)
        self.update_page(sel_last=sel_last)
        
    def area_resize(self, e):
        # updating main canvas
        self.area_size = (e.width - self.vbar_size, e.height - self.hbar_size)
        self.update_canvas()
        # updating nav panel
        ws = (self.root.winfo_width(), self.root.winfo_height())
        # checking if resizing happened (event could also be caused by pressing L (nav_change))
        if (ws != self.window_size):
            self.window_size = ws
            nn = self.nav_calc_n()
            # if different number of items can now fit on the screen, reset nav layout
            if nn != self.nav_n:
                self.nav_n = nn
                self.nav_place() 
                self.update_page()
        
    def update_canvas(self):
        w = min(self.area_size[0], self.img.size[0])
        h = min(self.area_size[1], self.img.size[1])
        cx = self.area_size[0] / 2 - w / 2
        cy = self.area_size[1] / 2 - h / 2
        self.canvas.place(x = cx, y = cy)
        self.canvas.config(width=w, height=h)
        self.canvas.create_image(0, 0, anchor='nw', image=self.photo)
        self.canvas.config(scrollregion=self.canvas.bbox('all'))
        self.canvas.config(scrollregion=(0, 0, self.img.size[0], self.img.size[1]))
        if self.area_size[0] >= self.img.size[0] and self.area_size[1] >= self.img.size[1]:
            self.hbar.pack_forget()
            self.vbar.pack_forget()
        else:
            self.hbar.pack(fill='x', side='bottom')
            self.vbar.pack(fill='y', side='right')
        self.fill_boxes()
        if self.delcands[self.s + self.k]:
            self.overlay.pack(fill='both', expand=True)
        else:
            self.overlay.pack_forget()

    def fill_boxes(self):
        self.rids = []
        self.cids = []
        for x1, y1, x2, y2, cls in self.boxes[self.s+self.k]:
            #self.topx = self.canvas.xview()[0] * self.img.size[0]
            #self.topy = self.canvas.yview()[0] * self.img.size[1]
            #x1, x2 = self.topx + x1, self.topx + x2
            #y1, y2 = self.topy + y1, self.topy + y2
            coords = [p * self.scale for p in [x1, y1, x2, y2]]
            rid = self.canvas.create_rectangle(*coords, outline=self.colors[self.cli], width=2)
            cid = self.draw_class_label(*coords[:2], cls)
            self.rids.append(rid)
            self.cids.append(cid)
    
    def draw_class_label(self, x, y, ind, hide=False):
        stt = tk.HIDDEN if hide or self.hide_classes else tk.NORMAL
        return self.canvas.create_text(x - 1, y - 1, text=self.classes[ind], fill=self.colors[self.cli],
                                       anchor=tk.SW, font='TkDefaultFont 16 bold', state=stt)
    
    def close_enough(self, x1, y1, x2, y2, thresh=5):
        if abs(x1 - x2) <= thresh and abs(y1 - y2) <= thresh:
            return True
        return False

    def write_box(self, coords, cls):
        x1, y1, x2, y2 = [p / self.scale for p in coords]
        coords = int(x1), int(y1), int(x2 + 0.5), int(y2 + 0.5)
        return (*coords, cls)
    
    def click1(self, e):
        if self.mode.endswith('-keys'):
            return
        self.topx = self.canvas.xview()[0] * self.img.size[0]
        self.topy = self.canvas.yview()[0] * self.img.size[1]
        self.cx = self.topx + e.x # cx means click_x
        self.cy = self.topy + e.y # cy means click_y
        for i, rid in enumerate(self.rids):
            bx1, by1, bx2, by2 = self.canvas.coords(rid)
            check1 = self.close_enough(self.cx, self.cy, bx1, by1)
            check2 = self.close_enough(self.cx, self.cy, bx2, by2)
            if check1 or check2:
                self.i = i
                self.mode = 'edit1-start' if check1 else 'edit2-start'
                self.cx = bx1 if check1 else bx2
                self.cy = by1 if check1 else by2
                self.indicator = self.canvas.create_oval(
                    self.cx-7, self.cy-7, self.cx+7, self.cy+7,
                    fill=self.indic1, outline=self.indic1)
                return
        self.i = None
        self.mode = 'add-start'

    def move1(self, e):
        if self.mode.endswith('-keys'):
            return
        x1, x2 = self.cx, self.topx + e.x
        y1, y2 = self.cy, self.topy + e.y
        coords = (x1, y1, x2, y2)
        if self.mode == 'add-move':
            self.canvas.coords(self.rids[self.i], *coords)
        elif self.mode == 'edit1-move':
            self.canvas.itemconfig(self.cids[self.i], state=tk.HIDDEN)
            rid = self.rids[self.i]
            fx, fy = self.canvas.coords(rid)[-2:]
            if x2 < fx and y2 < fy:
                self.canvas.coords(rid, x2, y2, fx, fy)
                self.canvas.coords(self.indicator, x2-7, y2-7, x2+7, y2+7)
        elif self.mode == 'edit2-move':
            rid = self.rids[self.i]
            fx, fy = self.canvas.coords(rid)[:2]
            if fx < x2 and fy < y2:
                self.canvas.coords(rid, fx, fy, x2, y2)
                self.canvas.coords(self.indicator, x2-7, y2-7, x2+7, y2+7)
        elif not self.close_enough(*coords):
            if self.mode == 'add-start':
                self.i = 0
                rid = self.canvas.create_rectangle(*coords, outline=self.colors[self.cli], width=2)
                cid = self.draw_class_label(*coords[:2], -1, hide=True)
                self.cids.insert(0, cid)
                self.rids.insert(0, rid)
                self.boxes[self.s+self.k].insert(0, self.write_box(coords, -1))
                self.mode = 'add-move'
                self.status.config(text='Drag mouse to draw a new box')
            elif self.mode == 'edit1-start':
                self.mode = 'edit1-move'
                self.status.config(text='Drag mouse to move the top left corner of the box')
            elif self.mode == 'edit2-start':
                self.mode = 'edit2-move'
                self.status.config(text='Drag mouse to move the bottom right corner of the box')
    
    def release1(self, e):
        if self.mode.endswith('-keys'):
            return
        if self.mode.endswith('-move'):
            if hasattr(self, 'indicator') and self.indicator is not None:
                self.canvas.delete(self.indicator)
                self.indicator = None
            rid = self.rids[self.i]
            cid = self.cids[self.i]
            x1, y1, x2, y2 = self.canvas.coords(rid)
            final = min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
            self.canvas.coords(rid, *final)
            self.canvas.coords(cid, final[0] - 1, final[1] - 1)
            self.boxes[self.s+self.k][self.i] = self.write_box(final, self.boxes[self.s+self.k][self.i][4])
            if not self.hide_classes:
                self.canvas.itemconfig(cid, state=tk.NORMAL)
            self.status.config(text=self.def_status)
            self.mode = ''
            self.i = None
        elif self.mode.startswith('edit'):
            self.mode = self.mode.replace('-start', '') + '-keys'
            self.canvas.itemconfig(self.indicator, fill=self.indic2, outline=self.indic2)
            self.status.config(text=self.edit_status)

    def key_space(self, e=None):
        if self.mode.endswith('-keys'):
            # finishing box edit mode
            self.canvas.delete(self.indicator)
            self.indicator = None
            self.mode = ''
            self.i = None
            return
        # selecting next image
        if self.s + self.k < len(self.files) - 1:
            self.k += 1
            if self.k >= self.nav_n:
                self.next_page(None)
            else:
                self.update_selection()
        
    def key_back(self, e=None):
        if self.s + self.k > 0:
            self.k -= 1
            if self.k < 0:
                self.prev_page(None, sel_last=True)
            else:
                self.update_selection()

    def key_move(self, e, direction, step):
        if self.mode.endswith('-keys'):
            rid = self.rids[self.i]
            x1, y1, x2, y2 = self.canvas.coords(rid)
            is1 = '1' in self.mode
            if is1 and direction == 'left': x1 -= step
            elif is1 and direction == 'up': y1 -= step
            elif is1 and direction =='right' and x1 + step < x2: x1 += step
            elif is1 and direction =='down' and y1 + step < y2: y1 += step
            elif direction == 'left' and x2 - step > x1: x2 -= step
            elif direction == 'up' and y2 - step > y1: y2 -= step
            elif direction == 'right': x2 += step
            elif direction == 'down': y2 += step
            self.canvas.coords(rid, x1, y1, x2, y2)
            self.boxes[self.s+self.k][self.i] = self.write_box((x1, y1, x2, y2), self.boxes[self.s+self.k][self.i][4])
            if is1:
                self.canvas.coords(self.indicator, x1-7, y1-7, x1+7, y1+7)
                self.canvas.coords(self.cids[self.i], x1-1, y1-1)
            else:
                self.canvas.coords(self.indicator, x2-7, y2-7, x2+7, y2+7)

    def key_tab(self, e):
        if self.mode in ['', 'edit1-keys', 'edit2-keys'] and self.boxes[self.s+self.k]:
            self.status.config(text=self.edit_status)
            if self.mode == '':
                # starting with the topmost box
                tops = [bx[1] for bx in self.boxes[self.s+self.k]]
                self.i = min(range(len(tops)), key=tops.__getitem__)
                self.mode = 'edit1-keys'
                x, y = self.canvas.coords(self.rids[self.i])[:2]
            elif self.mode == 'edit1-keys':
                self.canvas.delete(self.indicator)
                self.mode = 'edit2-keys'
                x, y = self.canvas.coords(self.rids[self.i])[-2:]
            elif self.mode == 'edit2-keys':
                self.canvas.delete(self.indicator)
                self.mode = 'edit1-keys'
                # continuing top to bottom, left to right, i.e. selecting the closest one where >y1 (or ==y1 and >x1)
                cur_x, cur_top = self.boxes[self.s+self.k][self.i][:2]
                nxt_i, nxt_top = -1, 99999
                for ind, bx in enumerate(self.boxes[self.s+self.k]):
                    if ind != self.i and bx[1] < nxt_top and (bx[1] > cur_top or bx[1] == cur_top and bx[0] > cur_x):
                        nxt_top = bx[1]
                        nxt_i = ind
                # if it was already the lowest, circle back to the highest
                if nxt_i == -1:
                    tops = [bx[1] for bx in self.boxes[self.s+self.k]]
                    nxt_i = min(range(len(tops)), key=tops.__getitem__)
                self.i = nxt_i
                x, y = self.canvas.coords(self.rids[self.i])[:2]
            self.indicator = self.canvas.create_oval(x-7, y-7, x+7, y+7, fill=self.indic2, outline=self.indic2)
   
    def key_del(self, e):
        if self.mode.endswith('-keys'):
            # deleting selected box
            self.canvas.delete(self.indicator)
            self.indicator = None
            self.canvas.delete(self.rids[self.i])
            self.canvas.delete(self.cids[self.i])
            self.rids.pop(self.i)
            self.cids.pop(self.i)
            self.boxes[self.s+self.k].pop(self.i)
            self.mode = ''
            self.i = None
            return
        # mark/unmark selected image for deletion
        i = self.s + self.k
        self.delcands[i] = not self.delcands[i]
        self.thumbs[self.k].config(text='TO DEL' if self.delcands[i] else '')
        if self.delcands[i]:
            self.overlay.pack(fill='both', expand=True)
        else:
            self.overlay.pack_forget()
   
    def key_class(self, e, ind):
        if self.mode.endswith('-keys'):
            txt = self.classes[ind]
            self.canvas.itemconfig(self.cids[self.i], text=txt)
            bx = self.boxes[self.s+self.k][self.i]
            self.boxes[self.s+self.k][self.i] = (*bx[:4], ind)
    
    def click2(self, e):
        self.xmove = e.x
        self.ymove = e.y
        
    def move2(self, e):
        self.canvas.xview_scroll(self.xmove - e.x, 'units')
        self.canvas.yview_scroll(self.ymove - e.y, 'units')
        self.xmove = e.x
        self.ymove = e.y
        
    def zoom(self, e):
        if self.mode.endswith('-keys'):
            return
        prevscale = self.scale
        self.scale = round(self.scale / 0.2) * 0.2 # round to nearest multiple of 0.2 (for initial zoom)
        self.scale += 0.2 * e.delta / abs(e.delta)
        self.scale = max(self.scale, 0.2)
        self.scale = min(self.scale, 10)
        nw = int(self.orig.size[0] * self.scale)
        nh = int(self.orig.size[1] * self.scale)
        self.img = self.orig.resize((nw, nh))
        self.photo = PIL.ImageTk.PhotoImage(self.img)
        self.update_canvas()
        self.header.configure(text=self.header.cget('text')
                              .replace('%d%%' % int(round(prevscale * 100)),
                                       '%d%%' % int(round(self.scale * 100))))
    
    def change_color(self, e):
        self.cli += 1
        if self.cli >= len(self.colors):
            self.cli = 0
        for rid in self.rids:
            self.canvas.itemconfig(rid, outline=self.colors[self.cli])
        for cid in self.cids:
            self.canvas.itemconfig(cid, fill=self.colors[self.cli])
            
    def toggle_classes(self, e):
        self.hide_classes = not self.hide_classes
        for cid in self.cids:
            self.canvas.itemconfig(cid, state=tk.HIDDEN if self.hide_classes else tk.NORMAL)
    
    def init_data(self, updir, files, labels='bboxes.txt', delcands='delcands.txt', backup=False, readonly=False, start=0):
        self.updir = updir
        self.files = files
        self.lb_path = osp.join(updir, labels)
        self.dc_path = osp.join(updir, delcands)
        self.readonly = readonly
        self.classes = self.prep_classes()
        self.boxes = self.prep_boxes(backup, readonly)
        self.delcands = self.prep_delete_candidates(backup)
        self.s = self.k = start
        self.update_page()
    
    def prep_classes(self):
        pt = osp.join(self.updir, 'classes.txt')
        with open(pt, 'r', encoding='utf-8') as f:
            ret = {int(ln.split(':')[0]): ln.split(':')[1] for ln in f.read().splitlines()}
        ret[-1] = 'N/A'
        return ret
    
    def prep_boxes(self, backup, readonly):
        if not readonly:
            if not osp.isfile(self.lb_path):
                # creating new empty file
                with open(self.lb_path, 'w', encoding='utf-8') as f:
                    for fl in self.files:
                        f.write(fl + ': -\n')
                # don't do [[]] * len(self.files) or it will be one memory loc, many refs
                return [[] for _ in range(len(self.files))]
            elif backup:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M')
                shutil.copyfile(self.lb_path, self.lb_path.replace('.txt', '_%s.txt' % timestamp))
        with open(self.lb_path, 'r', encoding='utf-8') as f:
            txt = [ln.split(': ')[1] for ln in f.read().splitlines()]
            return [self.parse_box_line(t) for t in txt]

    def parse_box_line(self, ln):
        if ln == '-':
            return []
        res = []
        for bx in ln.split(', '):
            parts = [int(p) for p in bx.split(' ')]
            cls = -1 if len(parts) < 5 else parts[4]
            res.append(parts[:4] + [cls])
        return res

    def prep_delete_candidates(self, backup):
        res = [False] * len(self.files)
        if osp.isfile(self.dc_path):
            if backup:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M')
                shutil.copyfile(self.dc_path, self.dc_path.replace('.txt', '_%s.txt' % timestamp))
            with open(self.dc_path, 'r', encoding='utf-8') as f:
                idx = [int(ln) for ln in f.read().splitlines()]
            for i in idx:
                res[i] = True
        return res
    
    def save(self, e):
        if self.readonly:
            return
        with open(self.lb_path, 'w', encoding='utf-8') as f:
            for fn, bx in zip(self.files, self.boxes):
                if not bx:
                    f.write(fn + ': -\n')
                else:
                    bx = sorted(bx, key=lambda b: (b[0], b[1], b[2], b[3]))
                    f.write(fn + ': ' + ', '.join([' '.join([str(p) for p in b]) for b in bx]) + '\n')
        with open(self.dc_path, 'w', encoding='utf-8') as f:
            idx = [i for i, d in enumerate(self.delcands) if d]
            for i in idx:
                f.write(str(i) + '\n')
    
    def on_closing(self):
        #if tk.messagebox.askokcancel('Quit', 'Do you want to quit?'):
        self.save(None)
        self.root.quit()

    def show_help(self, e):
        hw = tk.Toplevel(self.root)
        hw.geometry('+%d+%d' % (self.root.winfo_rootx(), self.root.winfo_rooty()))
        label = tk.Label(hw, text=self.help_text)
        label.pack()
        hw.resizable(0, 0)
        hw.attributes("-toolwindow", True)
        hw.grab_set()
    
    def run(self):
        self.root.mainloop()

    
if __name__ == "__main__":
    import sys
    topdir = osp.dirname(osp.dirname(osp.abspath(__file__)))
    sys.path.append(topdir)
    from scripts.utils import list_files
           
    root_dir = 'D:/Data/LAP/anime'
    files = list_files(root_dir)[:5000]
    gui = LabelerGUI()
    
    gui.init_data(root_dir, files, 'labels_faces.txt', readonly=True)
    
    #gui.init_data(root_dir, files, labels='labels_faces.txt', start=2000)
    #gui.init_data(root_dir, files, labels='labels_heads.txt', start=79)
    
    #root_dir = 'D:/Data/LAP/anime'
    #files = list_files(root_dir)[:1000]
    #gui = LabelerGUI()
    #gui.init_data(root_dir, files, labels='labels_baseheads_1000.txt', readonly=True)
    
    #root_dir = 'D:/Data/WIDER/WIDER_train/images'
    #files = list_files(root_dir)
    #gui = LabelerGUI()
    #gui.init_data(root_dir, files, labels='../labels.txt', readonly=True, start=5000)
    
    gui.run()