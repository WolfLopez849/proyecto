PREVIEW = {
    "name": "file_organizer_preview",
    "description": (
        "Create a read-only preview for organizing direct files in one configured folder. "
        "Use this first. It never moves files and never scans subfolders."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "root": {
                "type": "string",
                "description": "An existing folder inside the plugin's configured allowed folders.",
            },
            "max_files": {
                "type": "integer",
                "description": "Maximum number of direct files to inspect (1-500; default 200).",
            },
        },
        "required": ["root"],
    },
}

APPLY = {
    "name": "file_organizer_apply",
    "description": (
        "Apply a file-organizer preview by moving files into type folders. "
        "This always requests explicit human approval in Hermes. Only use after the user reviews the preview."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "plan_id": {"type": "string", "description": "The plan_id returned by file_organizer_preview."},
        },
        "required": ["plan_id"],
    },
}

UNDO = {
    "name": "file_organizer_undo",
    "description": (
        "Undo a completed file-organization operation. This always requests explicit human approval in Hermes."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "operation_id": {"type": "string", "description": "The operation_id returned by file_organizer_apply."},
        },
        "required": ["operation_id"],
    },
}