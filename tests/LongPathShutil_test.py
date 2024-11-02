import importlib
import inspect
import sys
import types
import requests
from bs4 import BeautifulSoup

def test_function_and_signatures():
    response = requests.get(r"https://docs.python.org/3/library/shutil.html")
    if response.status_code != 200:
        raise ConnectionError(
            "Could not download needed metadata from the official shutil documentation."
        )

    soup = BeautifulSoup(response.content, "html.parser")
    source_links = soup.find_all("a", href=lambda href: href and href.endswith("shutil.py"))

    if len(source_links) != 1:
        raise ConnectionError(
            "Could not find source code link on the official documentation."
        )

    response2 = requests.get(source_links[0].attrs["href"])
    if response2.status_code != 200:
        raise ConnectionError("Could not download needed metadata from the shutil github.")

    soup2 = BeautifulSoup(response2.content, "html.parser")
    source_links2 = soup2.find_all(
        "a", href=lambda href: href and "raw" in href and href.endswith("shutil.py")
    )

    if len(source_links2) == 0:
        raise ConnectionError("Could not find raw source code link on github.")

    response3 = requests.get(source_links2[0].attrs["href"])
    if response3.status_code != 200:
        raise ConnectionError("Could not download needed raw code from the shutil github.")

    # create current official shutil module
    module_name = "official_shutil"
    new_module = types.ModuleType(module_name)
    exec(response3.text, new_module.__dict__)
    sys.modules[module_name] = new_module

    # compare modules
    def compare_modules(module1_name, module2_name):
        module1 = importlib.import_module(module1_name)
        module2 = importlib.import_module(module2_name)

        module1_callables = {
            name: obj
            for name, obj in inspect.getmembers(module1)
            if callable(obj)
            and not name.startswith("__")
            and not name.startswith("_")
            and not inspect.isclass(obj)
        }
        module2_callables = {
            name: obj
            for name, obj in inspect.getmembers(module2)
            if callable(obj)
            and not name.startswith("__")
            and not name.startswith("_")
            and not inspect.isclass(obj)
        }

        # module1_attributes = {
        #     name: obj
        #     for name, obj in inspect.getmembers(module1)
        #     if not callable(obj) and not name.startswith("__") and not name.startswith("_")
        # }
        # module2_attributes = {
        #     name: obj
        #     for name, obj in inspect.getmembers(module2)
        #     if not callable(obj) and not name.startswith("__") and not name.startswith("_")
        # }

        missing_methods = [
            name for name in module2_callables if name not in module1_callables
        ]
        if missing_methods:
            return False, f"Missing methods in '{module1_name}': {missing_methods}"

        for name in module2_callables:
            if name in module1_callables:
                if inspect.isfunction(module2_callables[name]) and inspect.isfunction(
                    module1_callables[name]
                ):
                    if list(
                        inspect.signature(module2_callables[name]).parameters.keys()
                    ) != list(inspect.signature(module1_callables[name]).parameters.keys()):
                        return (
                            False,
                            f"Function '{name}' has different signatures between '{module1_name}' and '{module2_name}'",
                        )
                else:
                    return False, f"Callable '{name}' differs in type between the modules"

        return True, "Modules are identical in terms of methods, classes, and attributes"


    result, message = compare_modules("LongPathShutil", "official_shutil")
    assert result, message
