#!/usr/bin/env python3
# =============================================================================
# Assignment Lottery
# Randomly assigns tasks to participants, no repeats unless there are more
# participants than assignments (in which case assignments wrap around).
#
# Files it creates:
#   - Any .json you save via "Save List" (stores assignments + participants)
#   - Any .txt or .csv you export after drawing
#
# To run: python3 assignment_lottery.py
# =============================================================================

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import random
import json
import csv


class LotteryApp:
    def __init__(self, window):
        self.window = window
        self.window.title("Assignment Lottery")
        self.window.resizable(True, True)

        # Stores the last draw results as a list of (participant, assignment) tuples.
        # Used by export functions. Gets wiped when user clicks "Clear Results".
        self.last_results = []

        self.build_ui()

    # ── UI SETUP ──────────────────────────────────────────────────────────────
    # Everything visual is built here once at startup.
    # If you want to add a new button or widget, this is where to put it.

    def build_ui(self):
        self.window.configure(bg="#f4f6ff")
        self.window.minsize(620, 520)

        # ── Title area ──
        tk.Label(self.window, text="🎲 Assignment Lottery", font=("TkDefaultFont", 16, "bold"),
                 bg="#f4f6ff").pack(pady=(16, 0))
        tk.Label(self.window, text="Randomly assign tasks to participants",
                 font=("TkDefaultFont", 10), fg="#888", bg="#f4f6ff").pack(pady=(2, 12))

        # ── Save / Load bar ──
        # Buttons trigger file dialogs — no hardcoded paths.
        bar = tk.Frame(self.window, bg="#f4f6ff")
        bar.pack(fill="x", padx=12, pady=6)

        tk.Button(bar, text="💾 Save List", command=self.save_list,
                  bg="#4f8ef7", fg="white", relief="flat", padx=10).pack(side="left", padx=(0, 6))
        tk.Button(bar, text="📂 Load List", command=self.load_list,
                  bg="#6c757d", fg="white", relief="flat", padx=10).pack(side="left")

        # ── Two text input areas (side by side) ──
        # Left = assignments, Right = participants, both one item per line.
        cols = tk.Frame(self.window, bg="#f4f6ff")
        cols.pack(fill="both", expand=True, padx=12, pady=6)
        cols.columnconfigure(0, weight=1)  # left column stretches with window
        cols.columnconfigure(1, weight=1)  # right column stretches with window

        tk.Label(cols, text="Assignments (one per line)", font=("TkDefaultFont", 10, "bold"),
                 bg="#f4f6ff").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.assign_text = tk.Text(cols, width=28, height=14, relief="solid", bd=1,
                                   font=("TkDefaultFont", 11))
        self.assign_text.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        self.assign_text.insert("1.0", "task here")  # placeholder

        tk.Label(cols, text="Participants (one per line)", font=("TkDefaultFont", 10, "bold"),
                 bg="#f4f6ff").grid(row=0, column=1, sticky="w", pady=(0, 4))
        self.part_text = tk.Text(cols, width=28, height=14, relief="solid", bd=1,
                                 font=("TkDefaultFont", 11))
        self.part_text.grid(row=1, column=1, sticky="nsew")
        self.part_text.insert("1.0", "name here")  # placeholder

        cols.rowconfigure(1, weight=1)  # text areas grow vertically when window resizes

        # ── Action buttons ──
        # Draw = run the lottery
        # Clear Results = wipe the table AND last_results (so export resets too)
        # Export .txt / .csv = save results to file (only works after drawing)
        btn_row = tk.Frame(self.window, bg="#f4f6ff")
        btn_row.pack(pady=8)
        tk.Button(btn_row, text="🎲  Draw!", command=self.draw,
                  bg="#4f8ef7", fg="white", font=("TkDefaultFont", 12, "bold"),
                  relief="flat", padx=20, pady=6).pack(side="left", padx=4)
        tk.Button(btn_row, text="Clear Results", command=self.clear_all,
                  bg="#e8edf8", fg="#333", relief="flat", padx=12, pady=6).pack(side="left", padx=4)
        tk.Button(btn_row, text="📄 Export .txt", command=self.export_txt,
                  bg="#28a745", fg="white", relief="flat", padx=12, pady=6).pack(side="left", padx=4)
        tk.Button(btn_row, text="📊 Export .csv", command=self.export_csv,
                  bg="#28a745", fg="white", relief="flat", padx=12, pady=6).pack(side="left", padx=4)

        # ── Results table ──
        # Shows draw results with alternating row colors for readability.
        # Scrollable in case there are many participants.
        result_frame = tk.Frame(self.window, bg="#f4f6ff")
        result_frame.pack(fill="both", expand=False, padx=12, pady=6)

        cols_cfg = ("#", "Participant", "Assignment")
        self.tree = ttk.Treeview(result_frame, columns=cols_cfg, show="headings", height=8)
        self.tree.heading("#", text="#")
        self.tree.heading("Participant", text="Participant")
        self.tree.heading("Assignment", text="Assignment")
        self.tree.column("#", width=36, anchor="center")
        self.tree.column("Participant", width=200)
        self.tree.column("Assignment", width=260)

        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Alternating row colors — "even" rows are light blue, "odd" rows are white
        self.tree.tag_configure("odd", background="#ffffff")
        self.tree.tag_configure("even", background="#f0f4ff")

        # ── Status bar ──
        # Single line at the bottom showing feedback (saved, loaded, drawn, exported, errors).
        self.status = tk.Label(self.window, text="", fg="#888", bg="#f4f6ff", font=("TkDefaultFont", 10))
        self.status.pack(pady=(0, 12))

    # ── DRAW ──────────────────────────────────────────────────────────────────

    def draw(self):
        # Read and clean both text boxes — strip whitespace, ignore blank lines
        assignments = [l.strip() for l in self.assign_text.get("1.0", "end").splitlines() if l.strip()]
        participants = [l.strip() for l in self.part_text.get("1.0", "end").splitlines() if l.strip()]

        if not assignments or not participants:
            messagebox.showerror("Missing data", "Both lists need at least one entry.")
            return

        # If there are enough assignments for everyone, each person gets a unique one.
        # If there are more participants than assignments, assignments repeat (wrap around).
        if len(assignments) >= len(participants):
            shuffled = random.sample(assignments, len(participants))
        else:
            shuffled = assignments[:]
            random.shuffle(shuffled)
            shuffled = [shuffled[i % len(shuffled)] for i in range(len(participants))]

        pairs = list(zip(participants, shuffled))
        self.last_results = pairs  # save for export use

        # Clear old table rows before inserting new results
        self.clear_results()
        for i, (who, gets) in enumerate(pairs):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", "end", values=(i + 1, who, gets), tags=(tag,))

        self.status.config(text=f"✅ {len(pairs)} assignments drawn.")

    # ── CLEAR ─────────────────────────────────────────────────────────────────

    def clear_results(self):
        # Only clears the table display — does NOT wipe last_results.
        # This is intentional: draw() calls this internally to refresh the table,
        # and we don't want to lose last_results right after saving it.
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.status.config(text="")

    def clear_all(self):
        # Full clear — wipes both the table and last_results.
        # This is what the "Clear Results" button calls.
        # After this, export buttons will ask you to draw first.
        self.clear_results()
        self.last_results = []

    # ── SAVE / LOAD ───────────────────────────────────────────────────────────
    # Both use file dialogs so the user picks where to save/load.
    # File format is JSON: { "assignments": "...", "participants": "..." }
    # The text is stored as a single string with \n between names,
    # matching exactly what's in the text boxes.

    def save_list(self):
        assignments = self.assign_text.get("1.0", "end").strip()
        participants = self.part_text.get("1.0", "end").strip()
        if not assignments and not participants:
            messagebox.showwarning("Nothing to save", "Both lists are empty.")
            return
        path = filedialog.asksaveasfilename(
            title="Save list",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return  # user cancelled the dialog
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"assignments": assignments, "participants": participants}, f, indent=2)
        self.status.config(text=f"✅ Saved to: {path}")

    def load_list(self):
        path = filedialog.askopenfilename(
            title="Open a saved list",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return  # user cancelled the dialog
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Replace both text boxes with loaded content
            self.assign_text.delete("1.0", "end")
            self.assign_text.insert("1.0", data.get("assignments", ""))
            self.part_text.delete("1.0", "end")
            self.part_text.insert("1.0", data.get("participants", ""))
            self.clear_results()  # wipe old results since lists changed
            self.status.config(text=f"📂 Loaded: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not load file:\n{e}")

    # ── EXPORT ────────────────────────────────────────────────────────────────
    # Both export functions check last_results first.
    # If empty (no draw done, or cleared), they warn the user.

    def export_txt(self):
        if not self.last_results:
            messagebox.showwarning("No results", "Draw first before exporting.")
            return
        path = filedialog.asksaveasfilename(
            title="Export as text",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return  # user cancelled
        with open(path, "w", encoding="utf-8") as f:
            f.write("Assignment Lottery Results\n")
            f.write("=" * 34 + "\n")
            for i, (who, gets) in enumerate(self.last_results, 1):
                f.write(f"{i}. {who} → {gets}\n")
        self.status.config(text=f"📄 Exported to: {path}")

    def export_csv(self):
        if not self.last_results:
            messagebox.showwarning("No results", "Draw first before exporting.")
            return
        path = filedialog.asksaveasfilename(
            title="Export as CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return  # user cancelled
        # newline="" is required by Python's csv module to avoid extra blank lines on Windows
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["#", "Participant", "Assignment"])  # header row
            for i, (who, gets) in enumerate(self.last_results, 1):
                writer.writerow([i, who, gets])
        self.status.config(text=f"📊 Exported to: {path}")


# ── ENTRY POINT ───────────────────────────────────────────────────────────────
# This block only runs when you execute the file directly (python3 assignment_lottery.py).
# It won't run if someone imports this file as a module.

if __name__ == "__main__":
    main_window = tk.Tk()
    app = LotteryApp(main_window)
    main_window.mainloop()
