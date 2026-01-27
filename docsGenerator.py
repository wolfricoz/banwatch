import inspect
import json
import os
import sys
from glob import glob

from discord.ext import commands

from project.data import CACHE, VERSION


class DocGenerator():

    def __init__(self):
        self.command_cache = {}
        self.start()
        self.create_cache_File()

    def start(self):
        print("===Generating Documentation===")
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        count = 1

        if os.path.exists('docs/commands/'):
            for f in os.listdir('docs/commands/'):
                os.remove(os.path.join('docs/commands/', f))

        for file in glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "modules", "*.py")):

            if file.split("\\")[-1].lower() in ['logs.py', 'lobbyevents.py', 'QueueTask.py', 'whitelist.py',
                                                'devtools.py', 'inviteinfo.py', 'tasks.py', 'databasetasks.py', 'refresher.py', 'security.py', 'queuetask.py']:
                continue

            self.load_file(file, nav=count)
            count += 1

    def load_file(self, file, nav=1):
        name = os.path.splitext(os.path.basename(file))[0]
        document = f"docs/commands/{name}.md"
        if name == "__init__":
            return
        # create the document
        for dirc in ["docs", "docs/commands"]:
            if not os.path.exists(dirc):
                os.mkdir(dirc)

        # add package prefix to name
        module_name = f"modules.{name}"
        module = __import__(module_name, fromlist=[name])

        with open(document, "w", encoding="utf-8") as docfile:

            for member in dir(module):
                # do something with the member named ``member``

                if member == name:
                    tclass = getattr(module, member)
                    if inspect.ismodule(tclass):

                        continue

                    print(f"- Documenting Module: {name}")
                    docfile.write(self.document_header(tclass, name, nav))

                    for _, member_obj in inspect.getmembers(module, inspect.isclass):
                        # Check if the class is defined in the module we are inspecting
                        if member_obj.__module__ == module_name:
                            # Correctly check for inheritance using the class objects
                            if issubclass(member_obj, (commands.Cog, commands.GroupCog)):
                                domain = name
                                break

                    for function in tclass.__dict__:
                        self.command_line(docfile, function, tclass, domain, )

    def document_header(self, module, module_name: str, nav):

        return f"""---
layout: default
title: {module_name}
parent: Commands
nav_order: {nav}
---

<h1>{module_name}</h1>
<h6>version: {VERSION}</h6>
<h6>Documentation automatically generated from docstrings.</h6>

{inspect.getdoc(module)}


"""

    def command_line(self, docfile, function, tclass, domain, cachefile=None):
        if function.startswith("_") or function.startswith('cog') or function.startswith('cog') or function.startswith(
                'before_'):
            return

        func_obj = getattr(tclass, function)
        if not (hasattr(func_obj, 'callback') or callable(func_obj)):
            return
        docstring = ""
        # Check if it's a decorated command with a callback
        if hasattr(func_obj, 'callback'):
            docstring = inspect.getdoc(func_obj.callback)
        # Check if it's a callable function
        elif callable(func_obj):
            docstring = inspect.getdoc(func_obj)

        if not docstring:
            docstring = "Missing Documentation"
        if docstring.startswith("skip") or docstring.startswith("[skip]"):
            return

        param_string = ""
        try:
            # Use the callback if it exists, otherwise use the function object itself
            target_func = func_obj.callback if hasattr(func_obj, 'callback') else func_obj
            sig = inspect.signature(target_func)
            # Filter out 'self' and 'interaction' from the parameters
            params = [p for p in sig.parameters if p not in ('self', 'interaction')]
            if params:
                # Format parameters like: <param1> <param2>
                param_string = " " + " ".join([f"<{p}>" for p in params])
        except (ValueError, TypeError):
            print("Could not retrieve signature for function:", function)
            # This can happen for objects that are not inspectable
            pass
        self.add_command_to_cache(domain, function, docstring)

        docfile.write(f"### `{function}`\n\n"
                      f"**Usage:** `/{domain.lower()} {function}{param_string}`\n\n"
                      f"> {docstring}\n\n"
                      f"---\n\n")

    def add_command_to_cache(self, domain, function, docstring):
        # if domain not in self.command_cache :
        # 	self.command_cache[domain] = {}
        # self.command_cache[domain][function] = docstring
        self.command_cache[function] = docstring

    def create_cache_File(self):
        print(f"===Creating command cache file===")
        with open(CACHE, "w", encoding="utf-8") as cachefile:
            json.dump(self.command_cache, cachefile, indent=4)
        print("===Command cache file created===")


DocGenerator()