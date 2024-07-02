import logging
import sqlite3
from pathlib import Path
import PyPDF2
import pytesseract
from PIL import Image, ImageDraw, ImageTk, ImageFont
import io
import re
import pandas as pd
import tkinter as tk
from tkinter import scrolledtext, Entry, Button, Frame, filedialog, Listbox, ttk
import anthropic
import os
from pdf2image import convert_from_path
import PIL.Image
import PIL.ImageTk

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_local_db():
    conn = sqlite3.connect('documents.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS documents
                 (id INTEGER PRIMARY KEY, name TEXT, content TEXT)''')
    conn.commit()
    return conn

def add_document_to_db(conn, name, content):
    c = conn.cursor()
    c.execute("INSERT INTO documents (name, content) VALUES (?, ?)", (name, content))
    conn.commit()

def get_document_from_db(conn, name):
    c = conn.cursor()
    c.execute("SELECT content FROM documents WHERE name=?", (name,))
    result = c.fetchone()
    return result[0] if result else None

def find_time_series(text):
    pattern = r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b'
    numbers = re.findall(pattern, text)
    time_series = [float(num.replace(',', '')) for num in numbers]
    return time_series

def create_default_logo():
    image = Image.new('RGB', (200, 200), color='white')
    draw = ImageDraw.Draw(image)
    draw.ellipse([10, 10, 190, 190], fill='#4a86e8')
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()
    draw.text((40, 80), "ФАМ", font=font, fill='white')
    return image

def load_pdf(file_path):
    pages = convert_from_path(file_path)
    return pages


import tkinter as tk
from tkinter import ttk
from pdf2image import convert_from_path
from PIL import Image, ImageTk


class PDFViewer(tk.Toplevel):
    def __init__(self, parent, pdf_path):
        super().__init__(parent)
        self.title("PDF Viewer")
        self.geometry("800x600")

        self.pages = convert_from_path(pdf_path)
        self.current_page = 0

        # Створюємо фрейм з прокруткою
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.main_frame)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Кнопки навігації
        self.btn_frame = ttk.Frame(self)
        self.btn_frame.pack(fill=tk.X)

        self.btn_prev = ttk.Button(self.btn_frame, text="Previous", command=self.prev_page)
        self.btn_prev.pack(side=tk.LEFT)

        self.btn_next = ttk.Button(self.btn_frame, text="Next", command=self.next_page)
        self.btn_next.pack(side=tk.RIGHT)

        self.page_label = ttk.Label(self.btn_frame, text="")
        self.page_label.pack(side=tk.TOP)

        self.display_page()

    def display_page(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if 0 <= self.current_page < len(self.pages):
            # Масштабуємо зображення до ширини вікна
            window_width = self.winfo_width()
            img = self.pages[self.current_page]
            img_ratio = img.width / img.height
            new_width = window_width - 20  # Невеликий відступ
            new_height = int(new_width / img_ratio)

            img_resized = img.resize((new_width, new_height), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img_resized)

            label = ttk.Label(self.scrollable_frame, image=photo)
            label.image = photo
            label.pack(pady=10)

            self.page_label.config(text=f"Page {self.current_page + 1} of {len(self.pages)}")

    def next_page(self):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.display_page()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.display_page()

class FinancialAssistantGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Фінансовий асистент місцевих громад")
        self.master.geometry("1200x800")
        self.master.configure(bg='#f0f0f0')

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TButton', background='#4a86e8', foreground='white', font=('Arial', 10, 'bold'))
        self.style.map('TButton', background=[('active', '#619ff0')])
        self.style.configure('TEntry', fieldbackground='white', font=('Arial', 10))
        self.style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))

        self.main_frame = ttk.Frame(master)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.chat_frame = ttk.Frame(self.main_frame)
        self.chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.logo_frame = ttk.Frame(self.chat_frame)
        self.logo_frame.pack(pady=(0, 10))

        self.load_logo()

        self.chat_history = scrolledtext.ScrolledText(
            self.chat_frame,
            wrap=tk.WORD,
            width=70,
            height=30,
            font=("Arial", 10),
            bg='white',
            fg='#333333',
        )
        self.chat_history.pack(fill=tk.BOTH, expand=True)
        self.chat_history.insert(tk.END, "Вітаю! Я фінансовий асистент місцевих громад. Чим можу допомогти?\n\n")
        self.chat_history.config(state='disabled')

        self.document_frame = ttk.Frame(self.main_frame)
        self.document_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(20, 0))

        self.document_label = ttk.Label(self.document_frame, text="Завантажені документи:")
        self.document_label.pack(pady=(0, 5))

        self.document_listbox = tk.Listbox(self.document_frame, bg='white', fg='#333333', font=("Arial", 10),
                                           selectbackground='#4a86e8')
        self.document_listbox.pack(fill=tk.BOTH, expand=True)
        self.document_listbox.bind("<Double-Button-1>", self.show_preview)

        self.input_frame = ttk.Frame(master)
        self.input_frame.pack(fill=tk.X, padx=20, pady=20)

        self.user_input = ttk.Entry(
            self.input_frame,
            width=70,
            font=("Arial", 10),
        )
        self.user_input.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))
        self.user_input.bind("<Return>", self.send_message)

        self.send_button = ttk.Button(
            self.input_frame,
            text="Надіслати",
            command=self.send_message,
        )
        self.send_button.pack(side=tk.LEFT)

        self.clear_button = ttk.Button(
            self.input_frame,
            text="Очистити контекст",
            command=self.clear_context,
        )
        self.clear_button.pack(side=tk.LEFT, padx=(10, 0))

        self.upload_button = ttk.Button(
            self.input_frame,
            text="Завантажити документи",
            command=self.upload_documents,
        )
        self.upload_button.pack(side=tk.LEFT, padx=(10, 0))

        self.load_logo_button = ttk.Button(
            self.input_frame,
            text="Завантажити лого",
            command=self.load_custom_logo,
        )
        self.load_logo_button.pack(side=tk.LEFT, padx=(10, 0))

        self.documents = {}
        self.client = anthropic.Anthropic(api_key="YOUR KEY")

    def load_logo(self):
        logo_path = 'logo.png'
        if os.path.exists(logo_path):
            logo_image = Image.open(logo_path)
        else:
            logo_image = create_default_logo()

        self.logo_tk = ImageTk.PhotoImage(logo_image)
        self.logo_label = ttk.Label(self.logo_frame, image=self.logo_tk, background='#f0f0f0')
        self.logo_label.pack()

    def load_custom_logo(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if file_path:
            logo_image = Image.open(file_path)
            self.logo_tk = ImageTk.PhotoImage(logo_image)
            self.logo_label.destroy()
            self.logo_label = ttk.Label(self.logo_frame, image=self.logo_tk, background='#f0f0f0')
            self.logo_label.pack()

    def send_message(self, event=None):
        user_message = self.user_input.get()
        if not user_message:
            return
        self.chat_history.config(state='normal')
        self.chat_history.insert(tk.END, f"Ви: {user_message}\n\n", 'user')
        self.chat_history.tag_configure('user', foreground='#0056b3', font=('Arial', 10, 'bold'))
        self.chat_history.config(state='disabled')
        self.user_input.delete(0, tk.END)

        response = self.get_claude_response(user_message)

        self.chat_history.config(state='normal')
        self.chat_history.insert(tk.END, f"Асистент: {response}\n\n", 'assistant')
        self.chat_history.tag_configure('assistant', foreground='#28a745', font=('Arial', 10, 'bold'))
        self.chat_history.config(state='disabled')
        self.chat_history.see(tk.END)

    def clear_context(self):
        self.chat_history.config(state='normal')
        self.chat_history.delete('1.0', tk.END)
        self.chat_history.insert(tk.END, "Вітаю! Я фінансовий асистент місцевих громад. Чим можу допомогти?\n\n",
                                 'assistant')
        self.chat_history.config(state='disabled')
        self.documents.clear()
        self.document_listbox.delete(0, tk.END)

    def upload_documents(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        for file_path in file_paths:
            file_name = Path(file_path).name
            self.documents[file_name] = file_path
            self.document_listbox.insert(tk.END, file_name)

        self.chat_history.config(state='normal')
        self.chat_history.insert(tk.END, f"Завантажено {len(file_paths)} документ(ів)\n\n", 'system')
        self.chat_history.tag_configure('system', foreground='#6c757d')
        self.chat_history.config(state='disabled')

    def get_claude_response(self, user_message):
        logger.debug(f"Відправляємо запит до Claude: {user_message[:100]}...")
        try:
            document_context = "\n".join([f"{name}: {self.extract_text_from_pdf(path)[:500]}..." for name, path in self.documents.items()])
            message = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                system="Ви - фахівець з підтримки фінансових органів місцевих громад. Відповідайте на запитання користувача, враховуючи контекст завантажених документів.",
                messages=[
                    {
                        "role": "user",
                        "content": f"Контекст документів:\n{document_context}\n\nЗапитання користувача: {user_message}"
                    }
                ]
            )
            return message.content[0].text
        except anthropic.APIError as e:
            logger.error(f"API помилка: {e}")
            return f"Вибачте, виникла помилка при обробці вашого запиту: {e}"
        except Exception as e:
            logger.error(f"Невідома помилка: {e}")
            return f"Вибачте, виникла неочікувана помилка: {e}"

    def show_preview(self, event):
        index = self.document_listbox.curselection()
        if index:
            file_name = self.document_listbox.get(index)
            file_path = self.documents.get(file_name)
            if file_path:
                PDFViewer(self.master, file_path)

    def extract_text_from_pdf(self, pdf_path):
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            extracted_text = ""
            for page in reader.pages:
                extracted_text += page.extract_text() or ""
        return extracted_text

if __name__ == "__main__":
    root = tk.Tk()
    app = FinancialAssistantGUI(root)
    root.mainloop()
