from objects.object_base import ObjectBase, ViewableMixin


class ViewableTestObject(ViewableMixin, ObjectBase):
    def __init__(self, name="Test Object", visible=True):
        super().__init__(
            name=name,
            visible=visible,
        )
