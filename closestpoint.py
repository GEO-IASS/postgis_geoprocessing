# -*- coding: utf-8 -*-

"""
***************************************************************************
    closestpoint.py
    ---------------------
    Date                 : January 2015
    Copyright            : (C) 2015 by Giovanni Manghi
    Email                : giovanni dot manghi at naturalgis dot pt
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Giovanni Manghi'
__date__ = 'January 2015'
__copyright__ = '(C) 2015, Giovanni Manghi'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

from processing.core.parameters import ParameterVector
from processing.core.parameters import ParameterString
from processing.core.parameters import ParameterNumber
from processing.core.parameters import ParameterBoolean
from processing.core.parameters import ParameterTableField
from processing.core.outputs import OutputVector
from processing.core.outputs import OutputHTML

from processing.tools.system import *
from processing.tools import dataobjects

from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.algs.gdal.GdalUtils import GdalUtils
from processing.tools.vector import ogrConnectionString, ogrLayerName

class closestpoint(GeoAlgorithm):

    OUTPUT_LAYER = 'OUTPUT_LAYER'
    INPUT_LAYER_A = 'INPUT_LAYER_A'
    INPUT_LAYER_B = 'INPUT_LAYER_B'
    FIELD_A = 'FIELD_A'
    FIELD_B = 'FIELD_B'
    FIELDS = 'FIELDS'
    MULTI = 'MULTI' 
    TABLE = 'TABLE'
    SCHEMA = 'SCHEMA'
    OPTIONS = 'OPTIONS'
    OUTPUT = 'OUTPUT'
    
    def getIcon(self):
        return  QIcon(os.path.dirname(__file__) + '/icons/postgis.png')

    def defineCharacteristics(self):
        self.name = 'Closest point (with distance)'
        self.group = 'Vector geoprocessing'

        self.addParameter(ParameterVector(self.INPUT_LAYER_A, '"FROM" layer',
                          [ParameterVector.VECTOR_TYPE_ANY], False))
        self.addParameter(ParameterTableField(self.FIELD_A, '"FROM" layer ID',
                          self.INPUT_LAYER_A, optional=False))
        self.addParameter(ParameterString(self.FIELDS, 'Attributes to keep of layer "FROM" (comma separated list). Aliasing permitted.',
                          '', optional=False))
        self.addParameter(ParameterVector(self.INPUT_LAYER_B, '"TO" layer',
                          [ParameterVector.VECTOR_TYPE_ANY], False))
        self.addParameter(ParameterTableField(self.FIELD_B, '"TO" layer layer ID',
                          self.INPUT_LAYER_B, optional=False))
        self.addParameter(ParameterBoolean(self.MULTI,
                          'Consider "TO" layer as one unique feature', True))
        self.addParameter(ParameterString(self.SCHEMA, 'Output schema',
                          'public', optional=False))
        self.addParameter(ParameterString(self.TABLE, 'Output table name',
                          'closest_point', optional=False))
        self.addParameter(ParameterString(self.OPTIONS, 'Additional creation options (see ogr2ogr manual)',
                          '', optional=True))
        self.addOutput(OutputHTML(self.OUTPUT, 'Output log'))
        
    def processAlgorithm(self, progress):
        inLayerA = self.getParameterValue(self.INPUT_LAYER_A)
        ogrLayerA = ogrConnectionString(inLayerA)[1:-1]
        layernameA = ogrLayerName(inLayerA)
        inLayerB = self.getParameterValue(self.INPUT_LAYER_B)
        ogrLayerB = ogrConnectionString(inLayerB)[1:-1]
        layernameB = ogrLayerName(inLayerB)
        fieldA = unicode(self.getParameterValue(self.FIELD_A))
        fieldB = unicode(self.getParameterValue(self.FIELD_B))
        dsUriA = QgsDataSourceURI(self.getParameterValue(self.INPUT_LAYER_A))
        geomColumnA = dsUriA.geometryColumn()
        dsUriB = QgsDataSourceURI(self.getParameterValue(self.INPUT_LAYER_B))
        geomColumnB = dsUriB.geometryColumn()
        layerA = dataobjects.getObjectFromUri(self.getParameterValue(self.INPUT_LAYER_A))
        geomTypeA = layerA.geometryType()
        wkbTypeA = layerA.wkbType()
        sridA = layerA.crs().postgisSrid()
        layerB = dataobjects.getObjectFromUri(self.getParameterValue(self.INPUT_LAYER_B))
        geomTypeB = layerB.geometryType()
        wkbTypeB = layerB.wkbType()
        sridB = layerB.crs().postgisSrid()
        fields = unicode(self.getParameterValue(self.FIELDS))
        multi = self.getParameterValue(self.MULTI)
        schema = unicode(self.getParameterValue(self.SCHEMA))
        table = unicode(self.getParameterValue(self.TABLE))

        if len(fields) > 0:           
           fieldstring = fields.replace(",", ", g1.")
           fieldstring = ", g1." + fieldstring           
        else:
           fieldstring = ""

        if multi:
           sqlstring = "-sql \"WITH temp_table AS (SELECT ST_Union(" + geomColumnB + ") AS geom FROM " + layernameB + ") SELECT (ST_ClosestPoint(g2.geom, g1." + geomColumnA + "))::geometry(POINT," + str(sridA) + ") AS geom, ST_Distance(g1." + geomColumnA + ",g2.geom) AS distance, g1." + fieldA + " AS id_from" + fieldstring +  " FROM " + layernameA + " AS g1, temp_table AS g2\" -nln " + schema + "." + table + " -lco FID=gid -lco GEOMETRY_NAME=geom -nlt POINT --config PG_USE_COPY YES -a_srs EPSG:" + str(sridA) + ""
        else:
           sqlstring = "-sql \"SELECT (ST_ClosestPoint(g2." + geomColumnB + ",g1." + geomColumnA + "))::geometry(Point," + str(sridA) + ") AS geom, ST_Distance(g1." + geomColumnA + ",g2." + geomColumnB + ") AS distance, g1." + fieldA + " AS id_from" + fieldstring + ", g2." + fieldB + " AS id_to FROM " + layernameA + " AS g1, " + layernameB + " AS g2\" -nln " + schema + "." + table + " -lco FID=gid -lco GEOMETRY_NAME=geom -nlt POINT --config PG_USE_COPY YES"

        options = unicode(self.getParameterValue(self.OPTIONS))

        arguments = []
        arguments.append('-f')
        arguments.append('PostgreSQL')
        arguments.append(ogrLayerA)
        arguments.append(ogrLayerA)
        arguments.append(sqlstring)
        arguments.append('-overwrite')
                
        if len(options) > 0:
            arguments.append(options)
        #print table   
        commands = []
        if isWindows():
            commands = ['cmd.exe', '/C ', 'ogr2ogr.exe',
                        GdalUtils.escapeAndJoin(arguments)]
        else:
            commands = ['ogr2ogr', GdalUtils.escapeAndJoin(arguments)]

        GdalUtils.runGdal(commands, progress)

        output = self.getOutputValue(self.OUTPUT)
        f = open(output, 'w')
        f.write('<pre>')
        for s in GdalUtils.getConsoleOutput()[1:]:
            f.write(unicode(s))
        f.write('</pre>')
        f.close()