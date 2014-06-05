# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
import hashlib
import os
import sys
from sgtk.platform.qt import QtCore, QtGui

from sgtk import TankError

class ActionManager(object):
    """
    Class that handles dishing out and executing QActions based on the hook configuration.
    """
    
    UI_AREA_MAIN = 0x1
    UI_AREA_DETAILS = 0x2
    UI_AREA_HISTORY = 0x3
    
    def __init__(self):
        """
        Constructor
        """
        self._app = sgtk.platform.current_bundle()
        
        # are we old school or new school with publishes?
        publish_entity_type = sgtk.util.get_published_file_entity_type(self._app.sgtk)
        
        if publish_entity_type == "PublishedFile":
            self._publish_type_field = "published_file_type"
        else:
            self._publish_type_field = "tank_type"
        
    
    def get_actions_for_publish(self, sg_data, ui_area):
        """
        Returns a list of actions for a publish.
        
        :param sg_data: shotgun data for a publish
        """
        publish_type_dict = sg_data.get(self._publish_type_field)
        if publish_type_dict is None:
            # this publish does not have a type
            publish_type = "undefined"
        else:
            publish_type = publish_type_dict["name"]
        
        # check if we have logic configured to handle this
        mappings = self._app.get_setting("action_mappings")
        # returns a structure on the form
        # { "Maya Scene": ["reference", "import"] }
        actions = mappings.get(publish_type, [])
        
        if len(actions) == 0:
            return []
        
        # cool so we have one or more actions for this publish type.
        # call out to hook to give us the specifics.
        
        # resolve UI area
        if ui_area == ActionManager.UI_AREA_DETAILS:
            ui_area_str = "details"
        elif ui_area == ActionManager.UI_AREA_HISTORY:
            ui_area_str = "history"
        elif ui_area == ActionManager.UI_AREA_MAIN:
            ui_area_str = "main"
        else:
            raise TankError("Unsupported UI_AREA. Contact support.")

        action_defs = []
        try:
            action_defs = self._app.execute_hook_method("actions_hook", 
                                                        "generate_actions", 
                                                        sg_publish_data=sg_data, 
                                                        actions=actions,
                                                        ui_area=ui_area_str)
        except Exception:
            self._app.log_exception("Could not execute generate_actions hook.")
            
            
            
        # create QActions
        actions = []
        for action_def in action_defs:
            name = action_def["name"]
            caption = action_def["caption"]
            params = action_def["params"]
            description = action_def["description"]
            
            a = QtGui.QAction(caption, None)
            a.setToolTip(description)
            a.triggered[()].connect(lambda n=name, sg=sg_data, p=params: self._execute_hook(n, sg, p))
            actions.append(a)
            
        return actions
            
    def has_actions(self, publish_type):
        """
        Returns true if the given publish type has any actions associated with it.
        
        :param publish_type: A Shotgun publish type (e.g. 'Maya Render')
        :returns: True if the current actions setup knows how to handle this.
        """
        mappings = self._app.get_setting("action_mappings")

        # returns a structure on the form
        # { "Maya Scene": ["reference", "import"] }
        my_mappings = mappings.get(publish_type, [])
        
        return len(my_mappings) > 0
        
    def get_actions_for_folder(self, sg_data):
        """
        Returns a list of actions for a folder object.
        """
        fs = QtGui.QAction("Show in the file system", None)
        fs.triggered[()].connect(lambda f=sg_data: self._show_in_fs(f))
        
        sg = QtGui.QAction("Show details in Shotgun", None)
        sg.triggered[()].connect(lambda f=sg_data: self._show_in_sg(f))

        sr = QtGui.QAction("Show in Screening Room", None)
        sr.triggered[()].connect(lambda f=sg_data: self._show_in_sr(f))
        
        return [fs, sg, sr]
    
    ########################################################################################
    # callbacks
    
    def _execute_hook(self, action_name, sg_data, params):
        """
        callback - executes a hook
        """
        self._app.log_debug("Calling scene load hook for %s. Params: %s. Sg data: %s" % (action_name, params, sg_data))
        
        try:
            self._app.execute_hook_method("actions_hook", 
                                          "execute_action", 
                                          name=action_name, 
                                          params=params, 
                                          sg_publish_data=sg_data)
        except Exception, e:
            self._app.log_exception("Could not execute execute_action hook.")
            QtGui.QMessageBox.critical(None, "Hook Error", "Error: %s" % e)
    
    def _show_in_sg(self, entity):
        """
        Callback - Shows a shotgun entity in the web browser
        
        :param entity: std sg entity dict with keys type, id and name
        """
        url = "%s/detail/%s/%d" % (self._app.sgtk.shotgun.base_url, entity["type"], entity["id"])                    
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def _show_in_sr(self, entity):
        """
        Callback - Shows a shotgun entity in screening room
        
        :param entity: std sg entity dict with keys type, id and name
        """
        url = "%s/page/screening_room?entity_type=%s&entity_id=%d" % (self._app.sgtk.shotgun.base_url, 
                                                                      entity["type"], 
                                                                      entity["id"])                    
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
    
    def _show_in_fs(self, entity):
        """
        Callback - Shows a shotgun entity in the file system
        
        :param entity: std sg entity dict with keys type, id and name
        """
        paths = self._app.sgtk.paths_from_entity(entity["type"], entity["id"])    
        for disk_location in paths:
                
            # get the setting        
            system = sys.platform
            
            # run the app
            if system == "linux2":
                cmd = 'xdg-open "%s"' % disk_location
            elif system == "darwin":
                cmd = 'open "%s"' % disk_location
            elif system == "win32":
                cmd = 'cmd.exe /C start "Folder" "%s"' % disk_location
            else:
                raise Exception("Platform '%s' is not supported." % system)
            
            exit_code = os.system(cmd)
            if exit_code != 0:
                self._engine.log_error("Failed to launch '%s'!" % cmd)
    
    
    
