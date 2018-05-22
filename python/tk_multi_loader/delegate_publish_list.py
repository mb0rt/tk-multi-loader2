# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
from sgtk.platform.qt import QtCore, QtGui
import datetime
from .model_latestpublish import SgLatestPublishModel

# import the shotgun_model and view modules from the shotgun utils framework
shotgun_model = sgtk.platform.import_framework("tk-framework-shotgunutils", "shotgun_model")
shotgun_view = sgtk.platform.import_framework("tk-framework-qtwidgets", "views")

from .ui.widget_publish_list import Ui_PublishListWidget
from .delegate_publish import PublishWidget, PublishDelegate
from . import model_item_data

class PublishListWidget(PublishWidget):
    """
    Fixed height thin list item type widget, used for the list mode in the main loader view.
    """

    def __init__(self, parent):
        """
        Constructor

        :param parent: QT parent object
        """
        PublishWidget.__init__(self, Ui_PublishListWidget, parent)

    def set_text(self, large_text, small_text):
        """
        Populate the lines of text in the widget

        :param large_text: Header text as string
        :param small_text: smaller text as string
        """
        self.ui.label_1.setText(large_text)
        self.ui.label_2.setText(small_text)

    @staticmethod
    def calculate_size():
        """
        Calculates and returns a suitable size for this widget.

        :returns: Size of the widget
        """
        return QtCore.QSize(200, 56)



class SgPublishListDelegate(PublishDelegate):
    """
    Delegate which 'glues up' the List widget with a QT View.
    """
    def _create_widget(self, parent):
        """
        Widget factory as required by base class. The base class will call this
        when a widget is needed and then pass this widget in to the various callbacks.

        :param parent: Parent object for the widget
        """
        return PublishListWidget(parent)

    def _format_folder(self, model_index, widget):
        """
        Formats the associated widget as a folder item.

        :param model_index: Model index to process
        :param widget: widget to adjust
        """

        # Extract the Shotgun data and field value from the model index.
        (sg_data, field_value) = model_item_data.get_item_data(model_index)

        # by default, just display the value
        main_text = field_value
        small_text = ""

        if isinstance(field_value, dict) and "name" in field_value and "type" in field_value:
            # intermediate node with entity link
            main_text = "<b>%s</b> <b style='color:#2C93E2'>%s</b>" % (field_value["type"], field_value["name"])

        elif isinstance(field_value, list):
            # this is a list of some sort. Loop over all elements and extract a comma separated list.
            # this can be a multi link field but also a field like a tags field or a non-entity link type field.
            formatted_values = []
            formatted_types = set()

            for v in field_value:
                if isinstance(v, dict) and "name" in v and "type" in v:
                    # This is a link field
                    name = v["name"]
                    if name:
                        formatted_values.append(name)
                        formatted_types.add(v["type"])
                else:
                    formatted_values.append(str(v))

            types = ", ".join(list(formatted_types))
            names = ", ".join(formatted_values)
            main_text = "<b>%s</b><br>%s" % (types, names)

        elif sg_data:
            # this is a leaf node
            main_text = "<b>%s</b> <b style='color:#2C93E2'>%s</b>" % (sg_data["type"], field_value)
            small_text = sg_data.get("description") or "No description given."

        widget.set_text(main_text, small_text)

    def _format_publish(self, model_index, widget):
        """
        Formats the associated widget as a publish item.

        :param model_index: Model index to process
        :param widget: widget to adjust
        """
        # Publish Name Version 002
        sg_data = shotgun_model.get_sg_data(model_index)

        item_name    = sg_data.get( 'name' ) or 'Unnamed'
        variant_name = sg_data.get( 'sg_version_type' ) or 'unVersioned'
        entity_type  = sg_data.get( 'entity',{} ).get( 'type' )
        version      = sg_data.get( 'version_number' )
        publish_type = sg_data.get( 'type' )
        author       = sg_data.get( 'created_by', {} ).get( 'name' ) or 'Unspecified Author'
        created_data = sg_data.get( 'created_at' ) or 0
        publish_type = sg_data.get( 'published_file_type',{} ).get( 'name' ) or "IDK"
        publish_task = sg_data.get( 'task.Task.step', {}).get( 'name' ) or "Unspecified Task"

        # -- colors
        publish_type_color_dict = {'Maya Scene':'#FEAADB', "Alembic Asset":'#FEDFA6', "Maya Material":'#B792E8', 'Alembic Camera':'#97C668', 'Alembic Animation':'#FCBD98', 'Alembic Mesh':'#F0819A'}

        publish_type_color  = publish_type_color_dict.get( publish_type, '#FFFFFF' )
        variant_name_color  = '#F6DC1A'
        task_name_color     = '#2C93E2'
        item_color          = '#FFFFFF'

        # -- to str
        version_str = "%03d" % version if version is not None else "N/A"

        # --- main text
        if entity_type == 'Shot':
            main_text = "<span style='color:{variant_color}'>{variant_name}</span> | <B style='color:{item_color}'>{item_name}</B> | v{version}".format( variant_color=variant_name_color, variant_name=variant_name.upper(), item_color=task_name_color, item_name=item_name,  version=version_str )

        elif entity_type == 'Asset':
            main_text = "<span style='color:{variant_color}'>{variant_name}</span> | <B style='color:{task_color}'>{task_name}</B> | v{version}".format( variant_color=variant_name_color, variant_name=variant_name.upper(), task_color=task_name_color, task_name=publish_task.capitalize(), version=version_str )

        # --- small text
        date_str = datetime.datetime.fromtimestamp(created_data).strftime('%Y-%m-%d %H:%M')

        small_text = "<B style='color:{type_color}'>{type}</B> by {author} at {date}".format( type_color=publish_type_color, type=publish_type, author=author, date=date_str )

        widget.set_text(main_text, small_text)

    def sizeHint(self, style_options, model_index):
        """
        Specify the size of the item.

        :param style_options: QT style options
        :param model_index: Model item to operate on
        """
        return PublishListWidget.calculate_size()
