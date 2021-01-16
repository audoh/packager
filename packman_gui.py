import sys
import tkinter as tk
from enum import Enum
from re import L
from typing import Iterable, List, NamedTuple, Optional, Tuple, Union

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


class LogView(tk.Frame):
    def __init__(self, master: Optional[tk.Misc] = None, background: Optional[str] = "white", height: Optional[Union[int, str]] = None, width: Optional[Union[int, str]] = None):
        super().__init__(master, height=str(height)
                         if height is not None else None, width=str(width) if width is not None else None)
        self.background = background

        self.el_labels: List[tk.Label] = []
        self.grid_propagate(0)

        self.el_canvas = tk.Canvas(
            self, background=background, highlightthickness=1)
        self.el_canvas.grid(row=0, column=0, sticky=tk.NSEW)

        self.el_scrollbar = tk.Scrollbar(self)
        self.el_scrollbar.grid(row=0, column=1, sticky=tk.NS)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.el_canvas.configure(yscrollcommand=self.el_scrollbar.set)
        self.el_scrollbar.configure(command=self.el_canvas.yview)

        self.el_frame = tk.Frame(self.el_canvas)
        self.el_canvas.create_window(
            (0, 0), window=self.el_frame, anchor=tk.NW)

    def line_write(self, text: str, color: Optional[str] = None) -> None:
        label = tk.Text(self.el_frame, background=self.background, foreground=color,
                        height=1, relief=tk.FLAT, maxundo=0)
        label.insert(tk.INSERT, text)
        label.configure(state=tk.DISABLED)
        label.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=0, pady=0)
        self.el_labels.append(label)
        self.el_canvas.configure(scrollregion=self.el_canvas.bbox("all"))

    def line_clear(self) -> None:
        for label in self.el_labels:
            label.pack_forget()
        self.el_labels.clear()


class Menu(tk.Menu):
    def __init__(self, master: Optional[tk.Misc] = None):
        super().__init__(master)
        self.create_submenus()

    def create_submenus(self) -> None:
        file = tk.Menu(self, tearoff=False)
        file.add_command(label="Exit", command=sys.exit)
        self.add_cascade(label="File", menu=file)


class Application(tk.Frame):

    def __init__(self, master: Optional[tk.Misc] = None):
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
                                   command=self.update_packman, justify=tk.RIGHT)
        self.el_update.grid(row=0, column=2, sticky=tk.EW)

        self.el_packages = tk.Listbox(self, selectmode=tk.EXTENDED)
        self.el_packages.grid(row=1, column=0, columnspan=3, sticky=tk.NSEW)
        self.el_packages.bind("<<ListboxSelect>>", self.update_buttons_state)

        self.rowconfigure(1, weight=1)
        self.columnconfigure(1, weight=1)

        button_panel = tk.Frame(self)

        self.el_install = tk.Button(
            button_panel, text="Install", command=self.install_selected, state=tk.DISABLED)
        self.el_install.grid(row=0, column=0, sticky=tk.EW)

        self.el_uninstall = tk.Button(
            button_panel, text="Uninstall", command=self.uninstall_selected, state=tk.DISABLED)
        self.el_uninstall.grid(row=0, column=1, sticky=tk.EW)

        self.el_validate = tk.Button(
            button_panel, text="Validate", command=self.validate_selected, state=tk.DISABLED)
        self.el_validate.grid(row=0, column=2, sticky=tk.EW)

        button_panel.grid(row=2, column=2)

        self.el_output = LogView(self, height=100)
        self.el_output.grid(row=10, column=0, columnspan=3, sticky=tk.EW)

    def update_buttons_state(self, trigger_event: Optional[tk.Event] = None) -> None:
        manifest = self.packman.manifest_deprecated()
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
        self.el_output.line_write(message, color="green")

    def show_error(self, message: str) -> None:
        self.el_output.line_write(message, color="red")

    def show_info(self, message: str) -> None:
        self.el_output.line_write(message)

    def clear_message(self) -> None:
        self.el_output.line_clear()

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
        manifest = self.packman.manifest_deprecated()
        self.set_packages((name, self.packman.package(name))
                          for name in manifest.packages)

    def refresh_packages(self) -> None:
        if self.filter_installed.get():
            self.refresh_installed_packages()
        else:
            self.refresh_all_packages()

    def install_selected(self) -> None:
        succeeded: List[str] = []
        failed: List[str] = []
        for name, _ in self.curselection():
            success = self.packman.install(name=name)
            if success:
                succeeded.append(name)
                self.show_success(f"installed {name}")
            else:
                failed.append(name)
                self.show_error(f"did not install {name}")
        self.update_buttons_state()

    def uninstall_selected(self) -> None:
        succeeded: List[str] = []
        failed: List[str] = []
        for name, _ in self.curselection():
            success = self.packman.uninstall(name=name)
            if success:
                succeeded.append(name)
                self.show_success(f"uninstalled {name}")
            else:
                failed.append(name)
                self.show_error(f"did not uninstall {name}")
        self.update_buttons_state()

    def validate_selected(self) -> None:
        invalid_files: List[str] = []
        for name, _ in self.curselection():
            for file in self.packman.validate(name=name):
                invalid_files.append(file)
                self.show_error(
                    f"invalid file (checksum mismatch): {file}")
        if not invalid_files:
            self.show_success("no invalid files")

    def update_packman(self) -> None:
        if self.packman.update():
            self.refresh_packages()
        else:
            self.show_info("no changes found")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Packman GUI")
    root.iconphoto(False, tk.PhotoImage(file="icon.png"))
    root.geometry("500x500")

    menu = Menu(root)
    root.config(menu=menu)

    app = Application(root)
    app.pack(fill=tk.BOTH, expand=True)

    root.mainloop()
