import tkinter as tk
from enum import Enum
from typing import Iterable, List, Tuple

from packman import Packman
from packman.models.configuration import Package


class SortKey(Enum):
    NAME = 0
    NICE_NAME = 1
    DEFAULT = NAME

    def get_key_from_tuple(self, tuple: Tuple[str, Package]) -> str:
        name, package = tuple
        return self.get_key(name, package)

    def get_key(self, name: str, package: Package) -> str:
        if self == SortKey.NAME:
            return name
        elif self == SortKey.NICE_NAME:
            return package


class Application(tk.Frame):

    def __init__(self, master=None):
        super().__init__(master)
        self.create_widgets()

        self.package_sort = SortKey.DEFAULT
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

        self.el_validate = tk.Button(
            self, text="Validate", command=self.validate_selected)
        self.el_validate.grid(row=2, column=2)

        self.el_success = tk.Label(
            self, text="succ", relief=tk.GROOVE, fg="green")
        self.el_error = tk.Label(self, text="fail", relief=tk.GROOVE, fg="red")
        self.el_info = tk.Label(self, text="info", relief=tk.GROOVE)

    def show_success(self, message: str) -> None:
        self.el_success.configure(text=message)
        self.el_success.grid(row=3, column=0, columnspan=3, sticky=tk.EW)

    def show_error(self, message: str) -> None:
        self.el_error.configure(text=message)
        self.el_error.grid(row=4, column=0, columnspan=3, sticky=tk.EW)

    def show_info(self, message: str) -> None:
        self.el_info.configure(text=message)
        self.el_info.grid(row=5, column=0, columnspan=3, sticky=tk.EW)

    def clear_message(self) -> None:
        self.el_error.grid_forget()
        self.el_success.grid_forget()
        self.el_info.grid_forget()

    def set_packages(self, packages: Iterable[Tuple[str, Package]], sorted=False) -> None:
        self.el_packages.delete(0, tk.END)
        if not sorted:
            if not isinstance(packages, list):
                packages = list(packages)
            packages.sort(key=self.package_sort.get_key_from_tuple)
        for name, package in packages:
            self.el_packages.insert(0, name)

    def refresh_all_packages(self) -> None:
        self.set_packages(self.packman.packages())

    def refresh_installed_packages(self) -> None:
        manifest = self.packman.manifest()
        self.set_packages((name, self.packman.package(name))
                          for name in manifest.packages)

    def refresh_packages(self) -> None:
        if self.filter_installed.get():
            self.refresh_installed_packages()
        else:
            self.refresh_all_packages()

    def install_selected(self) -> None:
        self.clear_message()
        succeeded: List[str] = []
        failed: List[str] = []
        for selection in self.el_packages.curselection():
            selection: int
            name = self.el_packages.get(selection)
            success = self.packman.install(name=name)
            if success:
                succeeded.append(name)
                self.show_success(f"installed: {', '.join(succeeded)}")
            else:
                failed.append(name)
                self.show_error(f"not installed: {', '.join(failed)}")

    def uninstall_selected(self) -> None:
        self.clear_message()
        succeeded: List[str] = []
        failed: List[str] = []
        for selection in self.el_packages.curselection():
            selection: int
            name = self.el_packages.get(selection)
            success = self.packman.uninstall(name=name)
            if success:
                succeeded.append(name)
                self.show_success(f"uninstalled: {', '.join(succeeded)}")
            else:
                failed.append(name)
                self.show_error(f"not uninstalled: {', '.join(failed)}")

    def validate_selected(self) -> None:
        self.clear_message()
        invalid_files: List[str] = []
        for selection in self.el_packages.curselection():
            selection: int
            name = self.el_packages.get(selection)
            for file in self.packman.validate(name=name):
                invalid_files.append(file)
                self.show_error(
                    f"invalid files: {', '.join(invalid_files)}")
        if not invalid_files:
            self.show_success("no invalid files")

    def update_packman(self) -> None:
        self.clear_message()
        if self.packman.update():
            self.refresh_packages()
        else:
            self.show_info("no changes found")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Packman")
    root.geometry("1000x1000")

    app = Application(root)
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    app.grid(row=0, column=0)

    app.mainloop()
