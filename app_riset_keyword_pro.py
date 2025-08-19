# Nama File: app_riset_keyword_pro.py
# Deskripsi: Aplikasi desktop lengkap untuk riset kata kunci mendalam dan analisis kompetisi SERP.
#
# Cara Menjalankan:
# 1. Pastikan Anda memiliki Python 3 terinstal.
# 2. Buka Terminal atau Command Prompt.
# 3. Instal library yang dibutuhkan dengan mengetik:
#    pip install requests beautifulsoup4
# 4. Jalankan aplikasi dengan mengetik:
#    python app_riset_keyword_pro.py

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import requests
from bs4 import BeautifulSoup
import json
import csv
from datetime import datetime
import time
import threading
import queue

# --- KONFIGURASI ---
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
GOOGLE_DOMAINS = {
    "Indonesia": "google.co.id",
    "Global (.com)": "google.com",
    "Malaysia": "google.com.my",
    "Singapura": "google.com.sg",
}

class KeywordResearchApp:
    """
    Kelas utama untuk aplikasi riset keyword dengan antarmuka Tkinter.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Digital Marketing AI Toolkit - Keyword Research Pro")
        self.root.geometry("800x650")

        self.thread_queue = queue.Queue()
        self.results_data = []
        self.is_running = False

        self.create_widgets()
        self.check_queue()

    def create_widgets(self):
        # --- Frame Utama ---
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Frame Input & Kontrol (Kiri) ---
        controls_frame = ttk.LabelFrame(main_frame, text="Kontrol & Pengaturan", padding="10")
        controls_frame.grid(row=0, column=0, padx=(0, 10), pady=(0, 10), sticky="ns")
        
        # Input Kata Kunci
        ttk.Label(controls_frame, text="Kata Kunci Utama:").grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.keyword_entry = ttk.Entry(controls_frame, width=30)
        self.keyword_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # Pilihan Domain Google
        ttk.Label(controls_frame, text="Target Negara:").grid(row=2, column=0, sticky="w", pady=(0, 5))
        self.domain_var = tk.StringVar(value=list(GOOGLE_DOMAINS.keys())[0])
        self.domain_menu = ttk.Combobox(controls_frame, textvariable=self.domain_var, values=list(GOOGLE_DOMAINS.keys()), state="readonly")
        self.domain_menu.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        # Kedalaman Pencarian
        ttk.Label(controls_frame, text="Kedalaman Riset:").grid(row=4, column=0, sticky="w", pady=(0, 5))
        self.depth_spinbox = ttk.Spinbox(controls_frame, from_=1, to=5, width=5)
        self.depth_spinbox.set(2)
        self.depth_spinbox.grid(row=5, column=0, sticky="w", pady=(0, 15))

        # Checkbox Analisis Kompetisi
        self.analyze_serp_var = tk.BooleanVar(value=True)
        self.analyze_serp_check = ttk.Checkbutton(controls_frame, text="Analisis Kompetisi (SERP)", variable=self.analyze_serp_var)
        self.analyze_serp_check.grid(row=6, column=0, sticky="w", pady=(0, 15))

        # Tombol Start & Stop
        self.start_button = ttk.Button(controls_frame, text="Mulai Riset", command=self.start_research_thread)
        self.start_button.grid(row=7, column=0, sticky="ew", pady=5)
        self.stop_button = ttk.Button(controls_frame, text="Hentikan", command=self.stop_research, state=tk.DISABLED)
        self.stop_button.grid(row=8, column=0, sticky="ew", pady=5)

        # --- Frame Hasil & Log (Kanan) ---
        results_frame = ttk.Frame(main_frame)
        results_frame.grid(row=0, column=1, rowspan=2, sticky="nsew")
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Notebook (Tabs)
        notebook = ttk.Notebook(results_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Tab Hasil
        results_tab = ttk.Frame(notebook, padding="5")
        notebook.add(results_tab, text="Hasil Kata Kunci")
        
        # Filter Frame
        filter_frame = ttk.Frame(results_tab)
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        self.filter_entry = ttk.Entry(filter_frame)
        self.filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.filter_entry.bind("<KeyRelease>", self.apply_filter)
        
        # Treeview untuk menampilkan hasil
        self.tree = ttk.Treeview(results_tab, columns=("No", "Keyword", "Competition"), show="headings")
        self.tree.heading("No", text="No")
        self.tree.heading("Keyword", text="Kata Kunci")
        self.tree.heading("Competition", text="Estimasi Kompetisi")
        self.tree.column("No", width=40, anchor="center")
        self.tree.column("Keyword", width=300)
        self.tree.column("Competition", width=150, anchor="e")
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Tab Log
        log_tab = ttk.Frame(notebook, padding="5")
        notebook.add(log_tab, text="Log Proses")
        self.log_area = scrolledtext.ScrolledText(log_tab, wrap=tk.WORD, state=tk.DISABLED)
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # --- Frame Progress Bar & Tombol Simpan ---
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=1, column=0, padx=(0, 10), sticky="ew")
        
        self.progress_bar = ttk.Progressbar(bottom_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill=tk.X, expand=True, pady=(10, 5))
        
        self.save_button = ttk.Button(bottom_frame, text="Simpan Hasil ke CSV", command=self.save_to_csv, state=tk.DISABLED)
        self.save_button.pack(fill=tk.X, pady=5)

    def log(self, message):
        """Menambahkan pesan ke log area di GUI secara thread-safe."""
        self.thread_queue.put(("log", message))

    def update_progress(self, value, max_value):
        """Mengupdate progress bar secara thread-safe."""
        self.thread_queue.put(("progress", (value, max_value)))

    def add_result_to_tree(self, result_data):
        """Menambahkan hasil ke treeview secara thread-safe."""
        self.thread_queue.put(("result", result_data))

    def check_queue(self):
        """Memeriksa antrian pesan dari thread dan mengupdate GUI."""
        try:
            while True:
                msg_type, data = self.thread_queue.get_nowait()
                if msg_type == "log":
                    self.log_area.config(state=tk.NORMAL)
                    self.log_area.insert(tk.END, f"{data}\n")
                    self.log_area.see(tk.END)
                    self.log_area.config(state=tk.DISABLED)
                elif msg_type == "progress":
                    value, max_value = data
                    self.progress_bar['maximum'] = max_value
                    self.progress_bar['value'] = value
                elif msg_type == "result":
                    self.results_data.append(data)
                    self.apply_filter() # Refresh treeview
                elif msg_type == "finish":
                    self.research_finished()
        except queue.Empty:
            pass
        self.root.after(100, self.check_queue)

    def apply_filter(self, event=None):
        """Menerapkan filter pada treeview berdasarkan input."""
        filter_text = self.filter_entry.get().lower()
        # Hapus item yang ada
        for item in self.tree.get_children():
            self.tree.delete(item)
        # Tambahkan item yang sesuai filter
        filtered_data = [res for res in self.results_data if filter_text in res["keyword"].lower()]
        for i, res in enumerate(filtered_data, 1):
            competition_text = f"{res['competition']:,}" if res['competition'] is not None else "N/A"
            self.tree.insert("", "end", values=(i, res["keyword"], competition_text))

    def start_research_thread(self):
        """Memulai proses riset dalam thread baru."""
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showerror("Error", "Kata kunci utama tidak boleh kosong!")
            return

        self.is_running = True
        self.results_data.clear()
        self.apply_filter() # Kosongkan treeview
        self.progress_bar['value'] = 0
        self.log_area.config(state=tk.NORMAL)
        self.log_area.delete('1.0', tk.END)
        self.log_area.config(state=tk.DISABLED)

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.save_button.config(state=tk.DISABLED)

        # Ambil parameter dari GUI
        depth = int(self.depth_spinbox.get())
        domain_key = self.domain_var.get()
        domain = GOOGLE_DOMAINS[domain_key]
        analyze_serp = self.analyze_serp_var.get()

        # Buat dan jalankan thread
        self.research_thread = threading.Thread(
            target=self.run_research,
            args=(keyword, depth, domain, analyze_serp),
            daemon=True
        )
        self.research_thread.start()

    def stop_research(self):
        """Menghentikan proses riset."""
        if self.is_running:
            self.is_running = False
            self.log("🛑 Proses dihentikan oleh pengguna...")
            self.stop_button.config(state=tk.DISABLED)

    def research_finished(self):
        """Dipanggil saat riset selesai atau dihentikan."""
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        if self.results_data:
            self.save_button.config(state=tk.NORMAL)
        messagebox.showinfo("Selesai", "Proses riset telah selesai.")

    def save_to_csv(self):
        """Menyimpan hasil ke file CSV."""
        if not self.results_data:
            messagebox.showwarning("Peringatan", "Tidak ada data untuk disimpan.")
            return
        
        base_keyword = self.keyword_entry.get().strip().replace(' ', '_')
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"hasil_riset_{base_keyword}_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        if not filepath:
            return

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["keyword", "competition"])
                writer.writeheader()
                writer.writerows(self.results_data)
            self.log(f"💾 Hasil berhasil disimpan ke: {filepath}")
            messagebox.showinfo("Sukses", f"Data berhasil disimpan ke {filepath}")
        except IOError as e:
            messagebox.showerror("Error", f"Gagal menyimpan file: {e}")

    # --- FUNGSI LOGIKA INTI (BERJALAN DI THREAD) ---
    def run_research(self, keyword, depth, domain, analyze_serp):
        """Fungsi utama yang menjalankan semua logika riset."""
        self.log("🚀 Riset dimulai...")
        self.log(f"   - Kata Kunci: {keyword}")
        self.log(f"   - Domain: {domain}")
        self.log(f"   - Kedalaman: {depth}")
        self.log(f"   - Analisis SERP: {'Aktif' if analyze_serp else 'Nonaktif'}")

        # 1. Riset Keyword Rekursif
        all_keywords = self._recursive_research([keyword], depth, domain)
        if not self.is_running:
            self.thread_queue.put(("finish", None))
            return
        
        # 2. Analisis Kompetisi (jika diaktifkan)
        if analyze_serp:
            self.log("\n🔬 Memulai analisis kompetisi SERP...")
            total_keywords = len(all_keywords)
            for i, kw in enumerate(all_keywords):
                if not self.is_running:
                    break
                self.log(f"   ({i+1}/{total_keywords}) Menganalisis '{kw}'...")
                competition = self._get_competition_estimate(kw, domain)
                result = {"keyword": kw, "competition": competition}
                self.add_result_to_tree(result)
                self.update_progress(i + 1, total_keywords)
                time.sleep(0.5) # Jeda sopan untuk tidak overload
        else:
            self.log("\nℹ️ Analisis kompetisi dilewati.")
            for i, kw in enumerate(all_keywords):
                result = {"keyword": kw, "competition": None}
                self.add_result_to_tree(result)
                self.update_progress(i + 1, len(all_keywords))

        self.log("\n✅ Riset Selesai!")
        self.thread_queue.put(("finish", None))

    def _get_google_suggestions(self, keyword, domain):
        """Mendapatkan saran dari Google Autocomplete."""
        if not self.is_running: return []
        url = f"http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={keyword}"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return json.loads(response.text)[1]
        except (requests.RequestException, json.JSONDecodeError):
            return []

    def _recursive_research(self, initial_keywords, max_depth, domain):
        """Melakukan pencarian rekursif."""
        found_keywords = set(initial_keywords)
        queue_to_process = list(initial_keywords)

        for depth in range(max_depth):
            if not self.is_running: break
            self.log(f"\n🔄 Memulai riset kedalaman Level {depth + 1}...")
            next_queue = set()
            if not queue_to_process:
                self.log("   - Antrian kosong, berhenti.")
                break

            for i, keyword in enumerate(queue_to_process):
                if not self.is_running: break
                self.log(f"   ({i+1}/{len(queue_to_process)}) Mencari turunan dari '{keyword}'")
                new_suggestions = self._get_google_suggestions(keyword, domain)
                for suggestion in new_suggestions:
                    if suggestion not in found_keywords:
                        next_queue.add(suggestion)
                time.sleep(0.1)
            
            if next_queue:
                self.log(f"   - Menemukan {len(next_queue)} kata kunci unik baru.")
                found_keywords.update(next_queue)
                queue_to_process = list(next_queue)
            else:
                self.log("   - Tidak ada kata kunci baru ditemukan.")
                break
        return sorted(list(found_keywords))

    def _get_competition_estimate(self, keyword, domain):
        """Mendapatkan estimasi jumlah hasil dari halaman pencarian Google."""
        if not self.is_running: return None
        headers = {'User-Agent': USER_AGENT}
        url = f"https://www.{domain}/search?q={keyword}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Mencari div dengan id 'result-stats'
            result_stats_div = soup.find('div', id='result-stats')
            if result_stats_div:
                stats_text = result_stats_div.get_text()
                # Ekstrak angka dari teks (misal: "About 1,230,000 results")
                parts = stats_text.split()
                for part in parts:
                    part = part.replace(',', '').replace('.', '')
                    if part.isdigit():
                        return int(part)
            return 0 # Jika div tidak ditemukan
        except requests.RequestException:
            return None # Error koneksi

if __name__ == "__main__":
    root = tk.Tk()
    app = KeywordResearchApp(root)
    root.mainloop()

