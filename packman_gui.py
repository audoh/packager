import sys
import tkinter as tk
from enum import Enum
from re import L
from typing import Iterable, List, Optional, Tuple

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


class Menu(tk.Menu):
    def __init__(self, master=None):
        super().__init__(master)
        self.create_submenus()

    def create_submenus(self) -> None:
        file = tk.Menu(self, tearoff=False)
        file.add_command(label="Exit", command=sys.exit)
        self.add_cascade(label="File", menu=file)


class Application(tk.Frame):

    def __init__(self, master=None):
        super().__init__(master)
        self.create_widgets()

        self.current_packages: List[Tuple[str, Package]] = []
        self.package_sort = SortKey.DEFAULT
        self.packman = Packman()
        self.refresh_packages()

    def create_widgets(self) -> None:
        self.filter_installed = tk.BooleanVar(self, value=False)
        self.el_filter_installed = tk.Checkbutton(
            self, text="Installed", variable=self.filter_installed, command=self.refresh_packages)
        self.el_filter_installed.grid(row=0, column=0)

        self.el_update = tk.Button(self, text="Update",
                                   command=self.update_packman)
        self.el_update.grid(row=0, column=2)

        self.el_packages = tk.Listbox(self, selectmode="extended")
        self.el_packages.grid(row=1, column=0, columnspan=3, sticky=tk.NSEW)
        self.el_packages.bind("<<ListboxSelect>>", self.update_buttons_state)

        self.el_install = tk.Button(
            self, text="Install", command=self.install_selected, state=tk.DISABLED)
        self.el_install.grid(row=2, column=0)

        self.el_uninstall = tk.Button(
            self, text="Uninstall", command=self.uninstall_selected, state=tk.DISABLED)
        self.el_uninstall.grid(row=2, column=1)

        self.el_validate = tk.Button(
            self, text="Validate", command=self.validate_selected, state=tk.DISABLED)
        self.el_validate.grid(row=2, column=2)

        self.el_success = tk.Label(
            self, text="succ", relief=tk.GROOVE, fg="green")
        self.el_error = tk.Label(self, text="fail", relief=tk.GROOVE, fg="red")
        self.el_info = tk.Label(self, text="info", relief=tk.GROOVE)

    def update_buttons_state(self, trigger_event: Optional[tk.Event] = None) -> None:
        manifest = self.packman.manifest()
        any_installed = False
        any_uninstalled = False
        for name, _ in self.curselection():
            if name in manifest.packages:
                any_installed = True
            else:
                any_uninstalled = True
            if any_installed and any_uninstalled:
                break

        if any_uninstalled:
            self.el_install.configure(state=tk.NORMAL)
        else:
            self.el_install.configure(state=tk.DISABLED)

        if any_installed:
            self.el_uninstall.configure(state=tk.NORMAL)
            self.el_validate.configure(state=tk.NORMAL)
        else:
            self.el_uninstall.configure(state=tk.DISABLED)
            self.el_validate.configure(state=tk.DISABLED)

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
        if not isinstance(packages, list):
            packages = list(packages)
        if not sorted:
            packages.sort(key=self.package_sort.get_key_from_tuple)
        self.current_packages = packages
        self.el_packages.insert(0, *(name for name, _ in packages))

    def curselection(self) -> Iterable[Tuple[str, Package]]:
        for index in self.el_packages.curselection():
            index: int
            yield self.current_packages[index]

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
        for name, _ in self.curselection():
            success = self.packman.install(name=name)
            if success:
                succeeded.append(name)
                self.show_success(f"installed: {', '.join(succeeded)}")
            else:
                failed.append(name)
                self.show_error(f"not installed: {', '.join(failed)}")
        self.update_buttons_state()

    def uninstall_selected(self) -> None:
        self.clear_message()
        succeeded: List[str] = []
        failed: List[str] = []
        for name, _ in self.curselection():
            success = self.packman.uninstall(name=name)
            if success:
                succeeded.append(name)
                self.show_success(f"uninstalled: {', '.join(succeeded)}")
            else:
                failed.append(name)
                self.show_error(f"not uninstalled: {', '.join(failed)}")
        self.update_buttons_state()

    def validate_selected(self) -> None:
        self.clear_message()
        invalid_files: List[str] = []
        for name, _ in self.curselection():
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

    menu = Menu(root)
    root.config(menu=menu)

    app = Application(root)
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    app.grid(row=0, column=0)

    root.mainloop()
