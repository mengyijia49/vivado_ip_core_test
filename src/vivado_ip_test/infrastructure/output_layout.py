def binary_output_layout(fields):
    layout = {"encoding": "binary_msb_first", "fields": [
        {"name": name, "width": width} for name, width in fields]}
    output_field_slices(layout)
    return layout


def output_field_slices(layout):
    if (not isinstance(layout, dict) or layout.get("encoding") != "binary_msb_first"
            or not isinstance(layout.get("fields"), list) or not layout["fields"]):
        raise ValueError("Missing or unsupported output layout")
    offset, names, fields = 0, set(), []
    for field in layout["fields"]:
        if (not isinstance(field, dict) or set(field) != {"name", "width"}
                or not isinstance(field["name"], str) or not 1 <= len(field["name"]) <= 128
                or field["name"] in names or type(field["width"]) is not int or field["width"] < 1):
            raise ValueError("Invalid or duplicate output field")
        names.add(field["name"])
        fields.append((field["name"], offset, offset+field["width"]))
        offset += field["width"]
    return tuple(fields)
