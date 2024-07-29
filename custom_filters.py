from django import template

register = template.Library()

@register.filter
def all_elements_same_type(elements):
    if not elements:
        return False
    element_type = elements[0].get('element_type')  # Use .get to access dictionary key
    return all(element.get('element_type') == element_type for element in elements)

@register.filter
def get_element_type(elements):
    if elements:
        return elements[0].get('element_type')  # Use .get to access dictionary key
    return ''
