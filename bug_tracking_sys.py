import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import mysql.connector
from mysql.connector import Error

HOST = "127.0.0.1"
PORT = 3306  # Change to 3307 if your MySQL Server uses that port
USER = "root"
DATABASE = "bug_tracking_db"

class BugTrackingApp:
    def __init__(self, root, db_password):
        self.root = root
        self.root.title("Software Bug Reporting & Tracking System")
        self.root.geometry("1050x650")
        self.root.minsize(850, 550)
        self.db_password = db_password
        self.connection = None
        self.selected_bug_id = None

        try:
            self.setup_database()
        except Error as exc:
            messagebox.showerror(
                "MySQL connection failed",
                "Could not connect to MySQL.\n\n"
                f"Details: {exc}\n\n"
                "Check that MySQL80 is running, the root password is correct, "
                "and PORT matches your server (3306 or 3307)."
            )
            self.root.destroy()
            return

        self.build_ui()
        self.load_bugs()

    def setup_database(self):
        # Connect without selecting a database so the app can create it.
        server = mysql.connector.connect(
            host=HOST, port=PORT, user=USER, password=self.db_password
        )
        cursor = server.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE}")
        cursor.close()
        server.close()

        self.connection = mysql.connector.connect(
            host=HOST, port=PORT, user=USER, password=self.db_password,
            database=DATABASE
        )
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bugs (
                bug_id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(150) NOT NULL,
                description TEXT NOT NULL,
                priority ENUM('Low', 'Medium', 'High', 'Critical') NOT NULL DEFAULT 'Medium',
                status ENUM('Open', 'In Progress', 'Resolved', 'Closed') NOT NULL DEFAULT 'Open',
                reporter VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.connection.commit()
        cursor.close()

    def build_ui(self):
        heading = ttk.Label(
            self.root, text="Software Bug Reporting & Tracking System",
            font=("Segoe UI", 18, "bold")
        )
        heading.pack(pady=(12, 8))

        form = ttk.LabelFrame(self.root, text="Bug Details", padding=12)
        form.pack(fill="x", padx=14, pady=6)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        ttk.Label(form, text="Bug Title *").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.title_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.title_var).grid(
            row=0, column=1, sticky="ew", padx=5, pady=5
        )

        ttk.Label(form, text="Reporter *").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.reporter_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.reporter_var).grid(
            row=0, column=3, sticky="ew", padx=5, pady=5
        )

        ttk.Label(form, text="Priority").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.priority_var = tk.StringVar(value="Medium")
        ttk.Combobox(
            form, textvariable=self.priority_var,
            values=["Low", "Medium", "High", "Critical"], state="readonly", width=18
        ).grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(form, text="Status").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.status_var = tk.StringVar(value="Open")
        ttk.Combobox(
            form, textvariable=self.status_var,
            values=["Open", "In Progress", "Resolved", "Closed"],
            state="readonly", width=18
        ).grid(row=1, column=3, sticky="w", padx=5, pady=5)

        ttk.Label(form, text="Description *").grid(row=2, column=0, sticky="nw", padx=5, pady=5)
        self.description_text = tk.Text(form, height=4, wrap="word")
        self.description_text.grid(
            row=2, column=1, columnspan=3, sticky="ew", padx=5, pady=5
        )

        buttons = ttk.Frame(self.root)
        buttons.pack(fill="x", padx=14, pady=5)
        ttk.Button(buttons, text="Add Bug", command=self.add_bug).pack(side="left", padx=4)
        ttk.Button(buttons, text="Update Selected", command=self.update_bug).pack(side="left", padx=4)
        ttk.Button(buttons, text="Delete Selected", command=self.delete_bug).pack(side="left", padx=4)
        ttk.Button(buttons, text="Clear Form", command=self.clear_form).pack(side="left", padx=4)
        ttk.Button(buttons, text="Refresh", command=self.load_bugs).pack(side="right", padx=4)

        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=14, pady=(4, 12))
        columns = ("bug_id", "title", "priority", "status", "reporter", "created_at")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        headings = {
            "bug_id": "ID", "title": "Bug Title", "priority": "Priority",
            "status": "Status", "reporter": "Reporter", "created_at": "Created"
        }
        widths = {"bug_id": 55, "title": 300, "priority": 100, "status": 120,
                  "reporter": 140, "created_at": 170}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w")
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.status_label = ttk.Label(self.root, text=f"Connected to database: {DATABASE}")
        self.status_label.pack(anchor="w", padx=16, pady=(0, 8))

    def validate_form(self):
        title = self.title_var.get().strip()
        reporter = self.reporter_var.get().strip()
        description = self.description_text.get("1.0", "end").strip()
        if not title or not reporter or not description:
            messagebox.showwarning("Missing details", "Enter Bug Title, Reporter, and Description.")
            return None
        return title, description, self.priority_var.get(), self.status_var.get(), reporter

    def add_bug(self):
        values = self.validate_form()
        if not values:
            return
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO bugs (title, description, priority, status, reporter) "
            "VALUES (%s, %s, %s, %s, %s)", values
        )
        self.connection.commit()
        cursor.close()
        self.load_bugs()
        self.clear_form()
        messagebox.showinfo("Success", "Bug report added.")

    def update_bug(self):
        if self.selected_bug_id is None:
            messagebox.showwarning("Select a bug", "Select a bug from the table first.")
            return
        values = self.validate_form()
        if not values:
            return
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE bugs SET title=%s, description=%s, priority=%s, status=%s, reporter=%s "
            "WHERE bug_id=%s", (*values, self.selected_bug_id)
        )
        self.connection.commit()
        cursor.close()
        self.load_bugs()
        messagebox.showinfo("Success", "Bug report updated.")

    def delete_bug(self):
        if self.selected_bug_id is None:
            messagebox.showwarning("Select a bug", "Select a bug from the table first.")
            return
        if not messagebox.askyesno("Confirm delete", "Delete the selected bug report?"):
            return
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM bugs WHERE bug_id=%s", (self.selected_bug_id,))
        self.connection.commit()
        cursor.close()
        self.load_bugs()
        self.clear_form()
        messagebox.showinfo("Success", "Bug report deleted.")

    def load_bugs(self):
        if self.connection is None:
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT bug_id, title, priority, status, reporter, created_at "
            "FROM bugs ORDER BY bug_id DESC"
        )
        for row in cursor.fetchall():
            self.tree.insert("", "end", values=row)
        cursor.close()

    def on_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        row = self.tree.item(selected[0], "values")
        self.selected_bug_id = int(row[0])
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT title, description, priority, status, reporter FROM bugs WHERE bug_id=%s",
            (self.selected_bug_id,)
        )
        bug = cursor.fetchone()
        cursor.close()
        if bug:
            self.title_var.set(bug[0])
            self.description_text.delete("1.0", "end")
            self.description_text.insert("1.0", bug[1])
            self.priority_var.set(bug[2])
            self.status_var.set(bug[3])
            self.reporter_var.set(bug[4])

    def clear_form(self):
        self.selected_bug_id = None
        self.title_var.set("")
        self.reporter_var.set("")
        self.priority_var.set("Medium")
        self.status_var.set("Open")
        self.description_text.delete("1.0", "end")
        for item in self.tree.selection():
            self.tree.selection_remove(item)

    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
        self.root.destroy()

def main():
    root = tk.Tk()
    root.withdraw()
    password = simpledialog.askstring(
        "MySQL Login", "Enter your MySQL root password:", show="*"
    )
    if password is None:
        root.destroy()
        return
    root.deiconify()
    app = BugTrackingApp(root, password)
    if root.winfo_exists():
        root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()

if __name__ == "__main__":
    main()
    
