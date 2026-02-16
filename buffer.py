# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Buffer
                                 A QGIS plugin
 Plugin que aplica um buffer em uma camada vetorial
 ***************************************************************************/
"""

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.core import *
from .resources import *
from .buffer_dialog import BufferDialog
import os
import processing


class Buffer:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        self.camada = None
        self.saida = ""
        self.unidade = "metros"

        # Carregar tradução
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir, f'i18n/Buffer_{locale}.qm')
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.menu = self.tr(u'&Buffer')
        self.actions = []

    def tr(self, message):
        return QCoreApplication.translate('Buffer', message)

    def add_action(self, icon_path, text, callback, enabled_flag=True,
                   add_to_menu=True, add_to_toolbar=True, status_tip=None,
                   whats_this=None, parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip:
            action.setStatusTip(status_tip)
        if whats_this:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.iface.addToolBarIcon(action)
        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)
        return action

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        self.add_action(icon_path, text=self.tr(u'Buffer'),
                        callback=self.run, parent=self.iface.mainWindow())
        self.first_start = True

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&Buffer'), action)
            self.iface.removeToolBarIcon(action)

    def carregaVetor(self):
        self.dlg.comboBox.clear()
        lista_layers = QgsProject.instance().mapLayers().values()
        lista_layer_vetor = [layer.name() for layer in lista_layers if layer.type() == QgsMapLayer.VectorLayer]
        self.dlg.comboBox.addItems(lista_layer_vetor)

    def abrirVetor(self):
        caminho = QFileDialog.getOpenFileName(caption="Escolha a camada...", filter="Shapefile (*.shp)")[0]
        if caminho:
            layer = QgsVectorLayer(caminho, os.path.basename(caminho), "ogr")
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                self.carregaVetor()
            else:
                QMessageBox.warning(self.dlg, "Erro", "Não foi possível carregar a camada!")

    def camadaEnt(self):
        nomecamada = self.dlg.comboBox.currentText()
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.name() == nomecamada:
                return lyr
        return None

    def definirsaida(self):
        caminho = QFileDialog.getSaveFileName(caption="Define a layer de saída...",
                                              filter="Shapefile (*.shp)")[0]
        if caminho:
            self.dlg.lineEdit.setText(caminho)

    def variaveis(self):
        """Define atributos básicos para o buffer usando os nomes corretos"""
        self.camada = self.camadaEnt()
        self.saida = self.dlg.lineEdit.text() if self.dlg.lineEdit.text() else None
        self.unidade = self.dlg.comboUnidade.currentText() if self.dlg.comboUnidade else "metros"

    def criar_buffer(self):
        """Cria o buffer e adiciona ao projeto corretamente"""
        self.variaveis()

        if not self.camada:
            QMessageBox.warning(self.iface.mainWindow(), "Erro", "Selecione uma camada antes de criar o buffer.")
            return

        if not self.saida:
            self.saida = 'memory:buffer_temp'

        try:
            valor_buffer = float(self.dlg.doubleSpinBox.value())
        except ValueError:
            QMessageBox.warning(self.iface.mainWindow(), "Erro", "Digite um valor numérico para o buffer.")
            return

        # Conversão de unidades
        fator_unidade = 1.0
        if self.unidade.lower() == "quilômetros":
            fator_unidade = 1000
        elif self.unidade.lower() == "pés":
            fator_unidade = 0.3048
        elif self.unidade.lower() == "milhas":
            fator_unidade = 1609.34
        elif self.unidade.lower() == "graus":
            fator_unidade = 111320

        distancia = valor_buffer * fator_unidade

        params = {
            'INPUT': self.camada,
            'DISTANCE': distancia,
            'SEGMENTS': 5,
            'DISSOLVE': False,
            'OUTPUT': self.saida
        }

        try:
            buffer_result = processing.run("native:buffer", params)

            # Exibição correta do buffer no mapa
            if self.saida.startswith('memory:'):
                layer_saida = buffer_result['OUTPUT']
            else:
                layer_saida = QgsVectorLayer(self.saida, os.path.basename(self.saida), "ogr")

            if layer_saida and layer_saida.isValid():
                QgsProject.instance().addMapLayer(layer_saida)
                self.iface.mapCanvas().refresh()
                QMessageBox.information(self.iface.mainWindow(), "Sucesso", "Buffer criado e exibido no mapa!")
            else:
                QMessageBox.warning(self.dlg, "Erro", "Não foi possível carregar a camada de saída!")

        except Exception as e:
            QMessageBox.critical(self.dlg, "Erro ao criar buffer", str(e))

    def run(self):
        """Executa o plugin Buffer"""
        if self.first_start:
            self.first_start = False
            self.dlg = BufferDialog()

        self.dlg.show()
        self.carregaVetor()
        self.dlg.toolButton.clicked.connect(self.abrirVetor)
        self.dlg.toolButton_2.clicked.connect(self.definirsaida)

        result = self.dlg.exec_()
        if result:
            self.criar_buffer()

   