from . import schemas, tools


def register(ctx):
    def allowed_roots():
        return tools._configured_roots(ctx.get_config("allowed_roots", default=[]))

    ctx.register_tool(
        name=schemas.PREVIEW["name"],
        toolset="file_organizer",
        schema=schemas.PREVIEW,
        handler=lambda args, **kwargs: tools.preview_organize(args, allowed_roots(), ctx.state),
    )
    ctx.register_tool(
        name=schemas.APPLY["name"],
        toolset="file_organizer",
        schema=schemas.APPLY,
        handler=lambda args, **kwargs: tools.apply_organize(args, allowed_roots(), ctx.state),
    )
    ctx.register_tool(
        name=schemas.UNDO["name"],
        toolset="file_organizer",
        schema=schemas.UNDO,
        handler=lambda args, **kwargs: tools.undo_organize(args, allowed_roots(), ctx.state),
    )

    def require_human_approval(tool_name, args, **kwargs):
        if tool_name == schemas.APPLY["name"]:
            return {"action": "approve", "message": "Approve moving files using the reviewed preview?"}
        if tool_name == schemas.UNDO["name"]:
            return {"action": "approve", "message": "Approve restoring files to their original locations?"}
        return None

    ctx.register_hook("pre_tool_call", require_human_approval)