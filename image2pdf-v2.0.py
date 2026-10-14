import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import img2pdf
from PIL import Image

class ImageToPdfApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片转PDF高效处理工具 - 经典排版版")
        self.root.geometry("950x550")
        self.root.minsize(850, 450)
        
        # 核心数据结构：按顺序存储文件信息，保证左右行数绝对一致
        # 格式: [{'input': 'path.jpg', 'output': 'path.pdf', 'in_id': 'I001', 'out_id': 'I001'}, ...]
        self.file_data = []

        self._create_menu()
        self._create_ui()

    def _create_menu(self):
        """创建顶部菜单栏"""
        menubar = tk.Menu(self.root)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="软件说明", command=self.show_about)
        menubar.add_cascade(label="关于", menu=help_menu)
        self.root.config(menu=menubar)

    def _create_ui(self):
        """创建 左-中-右 经典布局界面"""
        # 主布局：左(权重1) - 中(固定) - 右(权重1) - 滚动条(固定)
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=0)
        self.root.columnconfigure(2, weight=1)
        self.root.columnconfigure(3, weight=0)
        self.root.rowconfigure(0, weight=1)

        # ================= 左侧面板 (输入) =================
        left_frame = ttk.Frame(self.root, padding=(15, 15, 5, 15))
        left_frame.grid(row=0, column=0, sticky="nsew")
        left_frame.rowconfigure(1, weight=1)
        left_frame.columnconfigure(0, weight=1)

        # 左侧顶部：选择文件按钮
        self.btn_select = ttk.Button(left_frame, text="📁 输入文件 (点击选择)", command=self.select_files)
        self.btn_select.grid(row=0, column=0, sticky="ew", pady=(0, 10), ipady=3)

        # 左侧表格
        self.tree_in = ttk.Treeview(left_frame, columns=("file",), show="headings", selectmode="extended")
        self.tree_in.heading("file", text="源图片文件 (双击预览)")
        self.tree_in.column("file", anchor=tk.W)
        self.tree_in.grid(row=1, column=0, sticky="nsew")
        self.tree_in.bind("<Double-1>", self.open_input_file)

        # ================= 中间面板 (转换按钮) =================
        middle_frame = ttk.Frame(self.root, padding=(5, 15))
        middle_frame.grid(row=0, column=1, sticky="ns")
        
        # 使用上下占位符让按钮垂直居中
        ttk.Frame(middle_frame).pack(expand=True, fill=tk.BOTH)
        
        # 绘制特色转换按钮 (扁平化商业风格)
        self.btn_convert = tk.Button(
            middle_frame, 
            text="执 行\n转 换\n▶▶", 
            font=("Microsoft YaHei", 11, "bold"),
            bg="#0078D7",        # 微软经典主题蓝
            fg="white",          # 白色文字
            relief="flat",       # 扁平无边框
            borderwidth=0,
            padx=15, pady=20,
            cursor="hand2",      # 鼠标放上去变成小手
            command=self.convert_to_pdf
        )
        self.btn_convert.pack(pady=10)
        
        # 添加鼠标悬停的变色反馈效果
        self.btn_convert.bind("<Enter>", lambda e: e.widget.config(bg="#005A9E"))
        self.btn_convert.bind("<Leave>", lambda e: e.widget.config(bg="#0078D7"))

        ttk.Frame(middle_frame).pack(expand=True, fill=tk.BOTH)

        # ================= 右侧面板 (输出) =================
        right_frame = ttk.Frame(self.root, padding=(5, 15, 0, 15))
        right_frame.grid(row=0, column=2, sticky="nsew")
        right_frame.rowconfigure(1, weight=1)
        right_frame.columnconfigure(0, weight=1)

        # 右侧顶部：状态标签
        self.lbl_status = ttk.Label(right_frame, text="📑 输出状态：等待导入...", font=("Microsoft YaHei", 9), foreground="gray")
        self.lbl_status.grid(row=0, column=0, sticky="ew", pady=(5, 12))

        # 右侧表格
        self.tree_out = ttk.Treeview(right_frame, columns=("status",), show="headings", selectmode="extended")
        self.tree_out.heading("status", text="输出 PDF 文件 (双击打开)")
        self.tree_out.column("status", anchor=tk.W)
        self.tree_out.grid(row=1, column=0, sticky="nsew")
        self.tree_out.bind("<Double-1>", self.open_output_file)

        # ================= 全局滚动条 (强制同步左右表格) =================
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.sync_scroll)
        scrollbar.grid(row=0, column=3, sticky="ns", pady=(48, 15), padx=(0, 15))
        
        self.tree_in.configure(yscrollcommand=scrollbar.set)
        self.tree_out.configure(yscrollcommand=scrollbar.set)
        
        # 绑定鼠标滚轮事件，确保滚轮滑动时两边绝对对齐
        self.tree_in.bind("<MouseWheel>", self.sync_mousewheel)
        self.tree_out.bind("<MouseWheel>", self.sync_mousewheel)


    def sync_scroll(self, *args):
        """拖动滚动条时，左右表格同步滚动"""
        self.tree_in.yview(*args)
        self.tree_out.yview(*args)

    def sync_mousewheel(self, event):
        """鼠标滚轮滚动时，左右表格同步滚动"""
        # Windows 系统中 event.delta 通常是 120 的倍数
        scroll_units = int(-1 * (event.delta / 120))
        self.tree_in.yview_scroll(scroll_units, "units")
        self.tree_out.yview_scroll(scroll_units, "units")
        return "break" # 阻止默认滚动，完全接管

    def select_files(self):
        """选择文件，直接写入左侧，右侧生成占位符"""
        filetypes = [
            ("图片文件", "*.jpg *.jpeg *.png *.bmp *.webp *.tif *.tiff *.gif"),
            ("所有文件", "*.*")
        ]
        files = filedialog.askopenfilenames(title="请选择图片文件（最多64个）", filetypes=filetypes)
        
        if not files:
            return
            
        if len(files) > 64:
            messagebox.showwarning("数量超限", "一次最多只能选择 64 个文件！已为您截取前 64 个。")
            files = files[:64]
            
        # 清空当前数据
        self.tree_in.delete(*self.tree_in.get_children())
        self.tree_out.delete(*self.tree_out.get_children())
        self.file_data.clear()
        
        # 逐行同时插入左右表格
        for f in files:
            filename = os.path.basename(f)
            in_id = self.tree_in.insert("", tk.END, values=(filename,))
            out_id = self.tree_out.insert("", tk.END, values=("—— 等待转换 ——",))
            
            self.file_data.append({
                'input': f,
                'output': None,
                'in_id': in_id,
                'out_id': out_id
            })
            
        self.lbl_status.config(text=f"📑 输出状态：已加载 {len(files)} 个文件", foreground="#0078D7")

    def convert_to_pdf(self):
        """执行转换"""
        if not self.file_data:
            messagebox.showwarning("提示", "请先在左侧输入图片文件！")
            return

        self.btn_select.config(state=tk.DISABLED)
        self.btn_convert.config(state=tk.DISABLED, bg="gray")
        self.lbl_status.config(text="📑 输出状态：正在拼命转换中...", foreground="#D83B01")

        success_count = 0
        
        for data in self.file_data:
            img_path = data['input']
            out_id = data['out_id']
            
            if not os.path.exists(img_path):
                self.tree_out.set(out_id, column="status", value="❌ 源文件已丢失")
                continue
                
            dir_name = os.path.dirname(img_path)
            base_name = os.path.splitext(os.path.basename(img_path))[0]
            pdf_path = os.path.join(dir_name, base_name + ".pdf")
            
            try:
                # 尝试 1：img2pdf 无损
                with open(img_path, "rb") as f:
                    pdf_bytes = img2pdf.convert(f.read())
                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)
                
                data['output'] = pdf_path
                self.tree_out.set(out_id, column="status", value=f"✅ {os.path.basename(pdf_path)}")
                success_count += 1
                
            except Exception:
                # 尝试 2：Pillow 降级
                try:
                    img = Image.open(img_path)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    img.save(pdf_path, "PDF", resolution=100.0)
                    
                    data['output'] = pdf_path
                    self.tree_out.set(out_id, column="status", value=f"✅ {os.path.basename(pdf_path)}")
                    success_count += 1
                except Exception:
                    self.tree_out.set(out_id, column="status", value="❌ 转换失败，格式不支持")

            # 同步焦点并滚动，产生动态效果
            self.tree_in.see(data['in_id'])
            self.tree_out.see(out_id)
            self.tree_out.selection_set(out_id)
            self.root.update()

        # 恢复 UI 状态
        self.btn_select.config(state=tk.NORMAL)
        self.btn_convert.config(state=tk.NORMAL, bg="#0078D7")
        self.lbl_status.config(text=f"📑 输出状态：完成！共转换 {success_count} 个文件", foreground="#107C41")
        messagebox.showinfo("转换完成", f"处理完毕！成功生成 {success_count} 个 PDF 文件。")

    def open_input_file(self, event):
        """双击左侧表格，打开图片"""
        selection = self.tree_in.selection()
        if not selection: return
        in_id = selection[0]
        
        # 根据 in_id 找到对应的文件路径
        for data in self.file_data:
            if data['in_id'] == in_id:
                path = data['input']
                if os.path.exists(path):
                    os.startfile(path)
                else:
                    messagebox.showerror("错误", "找不到图片文件。")
                break

    def open_output_file(self, event):
        """双击右侧表格，打开PDF"""
        selection = self.tree_out.selection()
        if not selection: return
        out_id = selection[0]
        
        for data in self.file_data:
            if data['out_id'] == out_id:
                path = data['output']
                if path and os.path.exists(path):
                    os.startfile(path)
                elif not path:
                    pass # 还没转换，忽略双击
                else:
                    messagebox.showerror("错误", "找不到生成的 PDF 文件。")
                break

    def show_about(self):
        """软件说明"""
        about_text = (
            "图片转PDF高效处理工具 v3.0 (经典布局版)\n\n"
            "【操作说明】\n"
            "1. 点击左上角直接导入图片，免去确认繁琐。\n"
            "2. 左右列表严格对照，滚轮滑动强制同步对齐。\n"
            "3. 蓝色的醒目按钮为转换引擎，点击即刻生成。\n"
            "4. 双侧均支持双击原生预览文件。\n\n"
            "【技术特性】\n"
            "双核转换：标准图片无损速转，特殊格式自动适配处理。\n\n"
            "版权所有 © 2026"
        )
        messagebox.showinfo("软件说明", about_text)


if __name__ == "__main__":
    # Windows 高 DPI 适配，防止界面模糊
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    root = tk.Tk()
    
    # 启用 ttk 主题
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    
    # 微调表格行高和字体
    style.configure("Treeview", rowheight=25, font=("Microsoft YaHei", 9))
    style.configure("Treeview.Heading", font=("Microsoft YaHei", 9, "bold"))
    
    app = ImageToPdfApp(root)
    root.mainloop()