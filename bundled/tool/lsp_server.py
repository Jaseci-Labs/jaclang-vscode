# Copyright (c) Jaseci Labs. All rights reserved.
# Licensed under the MIT License.
"""Implementation of tool support over LSP."""
from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Optional


# **********************************************************
# Update sys.path before importing any bundled libraries.
# **********************************************************
def update_sys_path(path_to_add: str, strategy: str) -> None:
    """Add given path to `sys.path`."""
    if path_to_add not in sys.path and os.path.isdir(path_to_add):
        if strategy == "useBundled":
            sys.path.insert(0, path_to_add)
        else:
            sys.path.append(path_to_add)


# Ensure that we can import LSP libraries, and other bundled libraries.
BUNDLE_DIR = pathlib.Path(__file__).parent.parent
BUNDLED_LIBS = os.fspath(BUNDLE_DIR / "libs")
# Always use bundled server files.
update_sys_path(os.fspath(BUNDLE_DIR / "tool"), "useBundled")
update_sys_path(
    BUNDLED_LIBS,
    os.getenv("LS_IMPORT_STRATEGY", "useBundled"),
)

# **********************************************************
# Imports needed for the language server goes below this.
# **********************************************************
import lsp_utils as utils
import lsprotocol.types as lsp
from pygls import server, uris

WORKSPACE_SETTINGS = {}
GLOBAL_SETTINGS = {}

MAX_WORKERS = 5
LSP_SERVER = server.LanguageServer(
    name="Jaseci", version="v0.0.1", max_workers=MAX_WORKERS
)
LSP_SERVER.workspace_filled = False
LSP_SERVER.dep_table = {}

# **********************************************************
# Language Server features
# **********************************************************

# Text Document Support


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls, params: lsp.DidChangeTextDocumentParams):
    """
    Things to happen on text document did change:
    1. Update the document tree
    2. Validate the document
    """
    utils.update_doc_tree(ls, params.text_document.uri)
    utils.validate(ls, params)


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
def did_save(ls, params: lsp.DidSaveTextDocumentParams):
    """
    Things to happen on text document did save:
    1. Update the document tree
    2. Validate the document
    3. Format the document (if enabled jaseci.format_on_save)
    """
    utils.update_doc_tree(ls, params.text_document.uri)
    utils.validate(ls, params)


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
def did_close(ls, params: lsp.DidCloseTextDocumentParams):
    """
    TODO Things to happen on text document did close:
    """
    pass


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls, params: lsp.DidOpenTextDocumentParams):
    """
    Things to happen on text document did open:
    1. If workspace is not filled, fill it.
    2. Validate the document
    """
    if not ls.workspace_filled:
        utils.fill_workspace(ls)
    utils.validate(ls, params)


@LSP_SERVER.feature(lsp.WORKSPACE_DID_DELETE_FILES)
def did_delete_files(ls, params: lsp.DeleteFilesParams):
    """
    TODO Things to happen on workspace did delete files:
    1. Set the workspace filled flag to False
    2. Remove the document from the workspace
    3. Check whether the document is a dependency of any other document
    4. If yes, Inform the user that the document is a dependency of other documents
    5. If no, delete the document
    """
    pass


@LSP_SERVER.feature(lsp.WORKSPACE_DID_RENAME_FILES)
def did_rename_files(ls, params: lsp.RenameFilesParams):
    """
    TODO Things to happen on workspace did rename files:
    1. Set the workspace filled flag to False
    2. Remove the document from the workspace
    3. Check whether the document is a dependency of any other document
    4. If yes, Inform the user that the document is a dependency of other documents
    5. If no, rename the document or fill the workspace
    """
    pass


@LSP_SERVER.feature(lsp.WORKSPACE_DID_CREATE_FILES)
def did_create_files(ls, params: lsp.CreateFilesParams):
    """
    TODO Things to happen on workspace did create files:
    1. Set the workspace filled flag to False
    2. Fill the workspace
    """
    pass


# Notebook Support


@LSP_SERVER.feature(lsp.NOTEBOOK_DOCUMENT_DID_OPEN)
async def did_open(ls, params: lsp.DidOpenNotebookDocumentParams):
    pass


@LSP_SERVER.feature(lsp.NOTEBOOK_DOCUMENT_DID_CLOSE)
async def did_open(ls, params: lsp.DidCloseNotebookDocumentParams):
    pass


@LSP_SERVER.feature(lsp.NOTEBOOK_DOCUMENT_DID_SAVE)
async def did_open(ls, params: lsp.DidSaveNotebookDocumentParams):
    pass


@LSP_SERVER.feature(lsp.NOTEBOOK_DOCUMENT_DID_CHANGE)
async def did_open(ls, params: lsp.DidChangeNotebookCellParams):
    pass


# Features


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_FORMATTING)
def formatting(ls, params: lsp.DocumentFormattingParams):
    """
    TODO Things to happen on text document formatting:
    1. Format the document
    """
    pass


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_COMPLETION)
def completions(params: Optional[lsp.CompletionParams] = None) -> lsp.CompletionList:
    """Returns completion items."""
    completion_items = utils.get_completion_items(LSP_SERVER, params)
    return lsp.CompletionList(is_incomplete=False, items=completion_items)


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DOCUMENT_HIGHLIGHT)
def document_highlight(ls, params: lsp.DocumentHighlightParams):
    """
    TODO Things to happen on text document document highlight:
    """
    pass


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DEFINITION)
def definition(ls, params: lsp.DefinitionParams):
    """
    TODO Things to happen on text document definition:
    """
    pass


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_HOVER)
def hover(ls, params: lsp.HoverParams):
    """
    TODO Things to happen on text document hover:
    """
    pass


# Symbol Handling


@LSP_SERVER.feature(lsp.WORKSPACE_SYMBOL)
def workspace_symbol(ls, params: lsp.WorkspaceSymbolParams):
    """Workspace symbols."""
    symbols = []
    for doc in ls.workspace.documents.values():
        if hasattr(doc, "symbols"):
            symbols.extend(doc.symbols)
        else:
            doc.symbols = utils.get_doc_symbols(ls, doc.uri)
            symbols.extend(doc.symbols)
    return symbols


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
def document_symbol(ls, params: lsp.DocumentSymbolParams):
    """Document symbols."""
    uri = params.text_document.uri
    doc = ls.workspace.get_document(uri)
    if not hasattr(doc, "symbols"):
        utils.update_doc_tree(ls, doc.uri)
        doc_symbols = utils.get_doc_symbols(ls, doc.uri)
        return [s for s in doc_symbols if s.location.uri == doc.uri]
    else:
        return [s for s in doc.symbols if s.location.uri == doc.uri]


# **********************************************************
# Required Language Server Initialization and Exit handlers.
# **********************************************************
@LSP_SERVER.feature(lsp.INITIALIZE)
def initialize(params: lsp.InitializeParams) -> None:
    """LSP handler for initialize request."""
    log_to_output(f"CWD Server: {os.getcwd()}")
    import_strategy = os.getenv("LS_IMPORT_STRATEGY", "useBundled")
    update_sys_path(os.getcwd(), import_strategy)

    GLOBAL_SETTINGS.update(**params.initialization_options.get("globalSettings", {}))

    settings = params.initialization_options["settings"]
    _update_workspace_settings(settings)
    log_to_output(
        f"Settings used to run Server:\r\n{json.dumps(settings, indent=4, ensure_ascii=False)}\r\n"
    )
    log_to_output(
        f"Global settings:\r\n{json.dumps(GLOBAL_SETTINGS, indent=4, ensure_ascii=False)}\r\n"
    )

    # Add extra paths to sys.path
    setting = _get_settings_by_path(pathlib.Path(os.getcwd()))
    for extra in setting.get("extraPaths", []):
        update_sys_path(extra, import_strategy)


# *****************************************************
# Internal functional and settings management APIs.
# *****************************************************
def _get_global_defaults():
    return {
        "path": GLOBAL_SETTINGS.get("path", []),
        "interpreter": GLOBAL_SETTINGS.get("interpreter", [sys.executable]),
        "args": GLOBAL_SETTINGS.get("args", []),
        "severity": GLOBAL_SETTINGS.get(
            "severity",
            {
                "error": "Error",
                "note": "Information",
            },
        ),
        "importStrategy": GLOBAL_SETTINGS.get("importStrategy", "useBundled"),
        "showNotifications": GLOBAL_SETTINGS.get("showNotifications", "off"),
        "extraPaths": GLOBAL_SETTINGS.get("extraPaths", []),
        "reportingScope": GLOBAL_SETTINGS.get("reportingScope", "file"),
    }


def _update_workspace_settings(settings):
    if not settings:
        key = utils.normalize_path(os.getcwd())
        WORKSPACE_SETTINGS[key] = {
            "cwd": key,
            "workspaceFS": key,
            "workspace": uris.from_fs_path(key),
            **_get_global_defaults(),
        }
        return

    for setting in settings:
        key = utils.normalize_path(uris.to_fs_path(setting["workspace"]))
        WORKSPACE_SETTINGS[key] = {
            **setting,
            "workspaceFS": key,
        }


def _get_settings_by_path(file_path: pathlib.Path):
    workspaces = {s["workspaceFS"] for s in WORKSPACE_SETTINGS.values()}

    while file_path != file_path.parent:
        str_file_path = utils.normalize_path(file_path)
        if str_file_path in workspaces:
            return WORKSPACE_SETTINGS[str_file_path]
        file_path = file_path.parent

    setting_values = list(WORKSPACE_SETTINGS.values())
    return setting_values[0]


# *****************************************************
# Logging and notification.
# *****************************************************
def log_to_output(
    message: str, msg_type: lsp.MessageType = lsp.MessageType.Log
) -> None:
    LSP_SERVER.show_message_log(message, msg_type)


def log_error(message: str) -> None:
    LSP_SERVER.show_message_log(message, lsp.MessageType.Error)
    if os.getenv("LS_SHOW_NOTIFICATION", "off") in ["onError", "onWarning", "always"]:
        LSP_SERVER.show_message(message, lsp.MessageType.Error)


def log_warning(message: str) -> None:
    LSP_SERVER.show_message_log(message, lsp.MessageType.Warning)
    if os.getenv("LS_SHOW_NOTIFICATION", "off") in ["onWarning", "always"]:
        LSP_SERVER.show_message(message, lsp.MessageType.Warning)


def log_always(message: str) -> None:
    LSP_SERVER.show_message_log(message, lsp.MessageType.Info)
    if os.getenv("LS_SHOW_NOTIFICATION", "off") in ["always"]:
        LSP_SERVER.show_message(message, lsp.MessageType.Info)


# *****************************************************
# Start the server.
# *****************************************************
if __name__ == "__main__":
    LSP_SERVER.start_io()
