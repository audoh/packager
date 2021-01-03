import tkinter as tk

from packman import Packman


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.create_widgets()

        self.packman = Packman()
        self.refresh_packages()

    def create_widgets(self):
        self.filter_installed = tk.BooleanVar(self, value=False)
        self.el_filter_installed = tk.Checkbutton(
            self, text="Installed", variable=self.filter_installed, command=self.refresh_packages)
        self.el_filter_installed.grid(row=0, column=0)

        self.el_update = tk.Button(self, text="Update",
                                   command=self.update_packman)
        self.el_update.grid(row=0, column=2)

        self.el_packages = tk.Listbox(self, selectmode="extended")
        self.el_packages.grid(row=1, column=0, columnspan=3, sticky=tk.NSEW)

        self.el_install = tk.Button(
            self, text="Install", command=self.install_selected)
        self.el_install.grid(row=2, column=0)

        self.el_uninstall = tk.Button(
            self, text="Uninstall", command=self.uninstall_selected)
        self.el_uninstall.grid(row=2, column=1)

        self.el_verify = tk.Button(
            self, text="Verify", command=self.verify_selected)
        self.el_verify.grid(row=2, column=2)

    def refresh_all_packages(self) -> None:
        self.el_packages.delete(0, tk.END)
        for name, package in self.packman.packages():
            self.el_packages.insert(0, name)

    def refresh_installed_packages(self) -> None:
        manifest = self.packman.manifest()
        self.el_packages.delete(0, tk.END)
        for name in manifest.packages:
            self.el_packages.insert(0, name)

    def refresh_packages(self) -> None:
        if self.filter_installed.get():
            self.refresh_installed_packages()
        else:
            self.refresh_all_packages()

    def install_selected(self) -> None:
        for selection in self.el_packages.curselection():
            selection: int
            name = self.el_packages.get(selection)
            self.packman.install(name=name)

    def uninstall_selected(self) -> None:
        for selection in self.el_packages.curselection():
            selection: int
            name = self.el_packages.get(selection)
            self.packman.uninstall(name=name)

    def verify_selected(self) -> None:
        for selection in self.el_packages.curselection():
            selection: int
            name = self.el_packages.get(selection)
            self.packman.verify(name=name)

    def update_packman(self) -> None:
        if self.packman.update():
            self.refresh_packages()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Packman")
    root.geometry("1000x1000")

    app = Application(root)
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    app.grid(row=0, column=0)

    app.mainloop()
