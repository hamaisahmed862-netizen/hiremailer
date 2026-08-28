def render_template(template: str, name: str, role: str) -> str:
    """
    Replaces {{name}} and {{role}} placeholders in a template string.
    Example: "Hi {{name}}, thanks for applying for {{role}}."
    """
    return template.replace("{{name}}", name).replace("{{role}}", role)