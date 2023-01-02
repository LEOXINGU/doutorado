# -*- coding: utf-8 -*-

"""
MRE.py
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""
__author__ = 'Leandro França'
__date__ = '2022-11-30'
__copyright__ = '(C) 2022, Leandro França'

from PyQt5.QtCore import *
from qgis.core import *
from numpy import sqrt, array, mean, std


class MRE(QgsProcessingAlgorithm):

    REF = 'REF'
    TESTE = 'TESTE'
    OUTPUT = 'OUTPUT'
    HTML = 'HTML'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return MRE()

    def name(self):
        return 'mre'

    def displayName(self):
        return self.tr('MRE - Retângulos Equivalentes')

    def group(self):
        return self.tr('Feições Lineares')

    def groupId(self):
        return 'feicoeslineares'

    def shortHelpString(self):
        return self.tr('''Esta ferramenta calcula as discrepâncias entre feições lineares pelo Método dos Retângulos Equivalentes (MRE).
Das discrepâncias planimétricas é determinado a classificação do Padrão de Exatidão Cartográfica para Produtos Cartográficos Digitais (PEC-PCD).
Autor: Leandro França - Eng. Cartógrafo''')

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.REF,
                self.tr('Linhas de referência'),
                [QgsProcessing.TypeVectorLine]
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.TESTE,
                self.tr('Polígonos das discrepâncias'),
                [QgsProcessing.TypeVectorPolygon]
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Distâncias Equivalentes')
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFileDestination(
                'HTML',
                'Relatório do PEC-PCD',
                self.tr('arquivo HTML (*.html)')
            )
        )
        
    def str2HTML(self, texto):
        if texto:
            dicHTML = {'Á': '&Aacute;',	'á': '&aacute;',	'Â': '&Acirc;',	'â': '&acirc;',	'À': '&Agrave;',	'à': '&agrave;',	'Å': '&Aring;',	'å': '&aring;',	'Ã': '&Atilde;',	'ã': '&atilde;',	'Ä': '&Auml;',	'ä': '&auml;',	'Æ': '&AElig;',	'æ': '&aelig;',	'É': '&Eacute;',	'é': '&eacute;',	'Ê': '&Ecirc;',	'ê': '&ecirc;',	'È': '&Egrave;',	'è': '&egrave;',	'Ë': '&Euml;',	'ë': '&Euml;',	'Ð': '&ETH;',	'ð': '&eth;',	'Í': '&Iacute;',	'í': '&iacute;',	'Î': '&Icirc;',	'î': '&icirc;',	'Ì': '&Igrave;',	'ì': '&igrave;',	'Ï': '&Iuml;',	'ï': '&iuml;',	'Ó': '&Oacute;',	'ó': '&oacute;',	'Ô': '&Ocirc;',	'ô': '&ocirc;',	'Ò': '&Ograve;',	'ò': '&ograve;',	'Ø': '&Oslash;',	'ø': '&oslash;',	'Ù': '&Ugrave;',	'ù': '&ugrave;',	'Ü': '&Uuml;',	'ü': '&uuml;',	'Ç': '&Ccedil;',	'ç': '&ccedil;',	'Ñ': '&Ntilde;',	'ñ': '&ntilde;',	'Ý': '&Yacute;',	'ý': '&yacute;',	'"': '&quot;', '”': '&quot;',	'<': '&lt;',	'>': '&gt;',	'®': '&reg;',	'©': '&copy;',	'\'': '&apos;', 'ª': '&ordf;', 'º': '&ordm', '°':'&deg;'}
            for item in dicHTML:
                if item in texto:
                    texto = texto.replace(item, dicHTML[item])
            return texto
        else:
            return ''

    def processAlgorithm(self, parameters, context, feedback):
        
        ref = self.parameterAsSource(
            parameters,
            self.REF,
            context
        )
        
        if ref is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.REF))
        
        teste = self.parameterAsSource(
            parameters,
            self.TESTE,
            context
        )

        if teste is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.TESTE))
        
        
        itens  = {
                     'discrep' : QVariant.Double,
                     'peso': QVariant.Double,
                     }
        
        Fields = QgsFields()
        
        for item in itens:
            Fields.append(QgsField(item, itens[item]))
            
        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            Fields,
            QgsWkbTypes.Polygon,
            ref.sourceCrs()
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))
        
        html_output = self.parameterAsFileOutput(
            parameters, 
            self.HTML, 
            context
        )

        
        PEC = { '0.5k': {'planim': {'A': {'EM': 0.14, 'EP': 0.085},'B': {'EM': 0.25, 'EP': 0.15},'C': {'EM': 0.4, 'EP': 0.25},'D': {'EM': 0.5, 'EP': 0.3}}, 'altim': {'A': {'EM': 0.135, 'EP': 0.085},'B': {'EM': 0.25, 'EP': 0.165},'C': {'EM': 0.3, 'EP': 0.2},'D': {'EM': 0.375, 'EP': 0.25}}},
        '1k': {'planim': {'A': {'EM': 0.28, 'EP': 0.17},'B': {'EM': 0.5, 'EP': 0.3},'C': {'EM': 0.8, 'EP': 0.5},'D': {'EM': 1, 'EP': 0.6}}, 'altim': {'A': {'EM': 0.27, 'EP': 0.17},'B': {'EM': 0.5, 'EP': 0.33},'C': {'EM': 0.6, 'EP': 0.4},'D': {'EM': 0.75, 'EP': 0.5}}},
        '2k': {'planim': {'A': {'EM': 0.56, 'EP': 0.34},'B': {'EM': 1, 'EP': 0.6},'C': {'EM': 1.6, 'EP': 1},'D': {'EM': 2, 'EP': 1.2}}, 'altim': {'A': {'EM': 0.27, 'EP': 0.17},'B': {'EM': 0.5, 'EP': 0.33},'C': {'EM': 0.6, 'EP': 0.4},'D': {'EM': 0.75, 'EP': 0.5}}},
        '5k': {'planim': {'A': {'EM': 1.4, 'EP': 0.85},'B': {'EM': 2.5, 'EP': 1.5},'C': {'EM': 4, 'EP': 2.5},'D': {'EM': 5, 'EP': 3}}, 'altim': {'A': {'EM': 0.54, 'EP': 0.34},'B': {'EM': 1, 'EP': 0.67},'C': {'EM': 1.2, 'EP': 0.8},'D': {'EM': 1.5, 'EP': 1}}},
        '10k': {'planim': {'A': {'EM': 2.8, 'EP': 1.7},'B': {'EM': 5, 'EP': 3},'C': {'EM': 8, 'EP': 5},'D': {'EM': 10, 'EP': 6}}, 'altim': {'A': {'EM': 1.35, 'EP': 0.84},'B': {'EM': 2.5, 'EP': 1.67},'C': {'EM': 3, 'EP': 2},'D': {'EM': 3.75, 'EP': 2.5}}},
        '25k': {'planim': {'A': {'EM': 7, 'EP': 4.25},'B': {'EM': 12.5, 'EP': 7.5},'C': {'EM': 20, 'EP': 12.5},'D': {'EM': 25, 'EP': 15}}, 'altim': {'A': {'EM': 2.7, 'EP': 1.67},'B': {'EM': 5, 'EP': 3.33},'C': {'EM': 6, 'EP': 4},'D': {'EM': 7.5, 'EP': 5}}},
        '50k': {'planim': {'A': {'EM': 14, 'EP': 8.5},'B': {'EM': 25, 'EP': 15},'C': {'EM': 40, 'EP': 25},'D': {'EM': 50, 'EP': 30}}, 'altim': {'A': {'EM': 5.5, 'EP': 3.33},'B': {'EM': 10, 'EP': 6.67},'C': {'EM': 12, 'EP': 8},'D': {'EM': 15, 'EP': 10}}},
        '100k': {'planim': {'A': {'EM': 28, 'EP': 17},'B': {'EM': 50, 'EP': 30},'C': {'EM': 80, 'EP': 50},'D': {'EM': 100, 'EP': 60}}, 'altim': {'A': {'EM': 13.7, 'EP': 8.33},'B': {'EM': 25, 'EP': 16.67},'C': {'EM': 30, 'EP': 20},'D': {'EM': 37.5, 'EP': 25}}},
        '250k': {'planim': {'A': {'EM': 70, 'EP': 42.5},'B': {'EM': 125, 'EP': 75},'C': {'EM': 200, 'EP': 125},'D': {'EM': 250, 'EP': 150}}, 'altim': {'A': {'EM': 27, 'EP': 16.67},'B': {'EM': 50, 'EP': 33.33},'C': {'EM': 60, 'EP': 40},'D': {'EM': 75, 'EP': 50}}}}
        
        dicionario = {'0.5k': '1:500', '1k': '1:1.000', '2k': '1:2.000', '5k': '1:5.000', '10k': '1:10.000', '25k': '1:25.000', '50k': '1:50.000', '100k': '1:100.000', '250k': '1:250.000'}
        
        valores = ['A', 'B', 'C', 'D']
        
        Escalas = [ esc for esc in dicionario]
        
        # Verificacoes
        # As duas camadas devem estar no mesmo SRC e estarem projetadas
        # As duas camadas devem ser do tipo linha
        crs1 = ref.sourceCrs()
        crs2 = teste.sourceCrs()
        distance = QgsDistanceArea()

        
        if not (crs1 == crs2 and not(crs1.isGeographic())):
            raise QgsProcessingException('SRC das camadas de entrada devem ser iguais e estar projetados!')

        
        feedback.pushInfo('Aplicando o o Método dos Retângulos Equivalentes...')
        
        
        # Calcular Discrepancias
        DISCREP = []
        COMPR = []
        total = 100.0 / teste.featureCount() if teste.featureCount() else 0
        
        for index, feat1 in enumerate(teste.getFeatures()):
            pol = feat1.geometry()
            compr = 0
            S = pol.area()
            p = pol.length()/2.0
            x1 = (p-sqrt(p*p-4*S))/2.0
            DISCREP += [float(x1)]
            for feat2 in ref.getFeatures():
                lin = feat2.geometry()
                if pol.intersects(lin):
                    inter = pol.intersection(lin)
                    if inter.type() == 1:
                        compr += inter.length()
            COMPR += [compr]
            
            feature = QgsFeature(Fields)
            feature.setGeometry(pol)
            feature.setAttributes([float(x1), float(compr)])
            sink.addFeature(feature, QgsFeatureSink.FastInsert)
            
            if feedback.isCanceled():
                break
            feedback.setProgress(int((index+1) * total))

        

        # Gerar relatorio do metodo
        DISCREP= array(DISCREP)
        COMPR = array(COMPR)
        EMQ = sqrt((DISCREP*DISCREP*COMPR).sum()/COMPR.sum())
        media_Pond =sum(DISCREP*COMPR)/sum(COMPR)
        RESULTADOS = {}
        for escala in Escalas:
            mudou = False
            for valor in valores[::-1]:
                EM = PEC[escala]['planim'][valor]['EM']
                EP = PEC[escala]['planim'][valor]['EP']
                if (sum((DISCREP<EM)*COMPR)/sum(COMPR))>0.9 and (EMQ < EP):
                    RESULTADOS[escala] = valor
                    mudou = True
            if not mudou:
                RESULTADOS[escala] = 'R'

        feedback.pushInfo('RESULTADOS:')
        feedback.pushInfo('Media: {} m'.format(round(DISCREP.mean(),3)))
        feedback.pushInfo('Media Ponderada das Discrepancias: {} m'.format(round(media_Pond,3)))
        feedback.pushInfo('REMQ Ponderado: {} m'.format(round(EMQ,3)))
        feedback.pushInfo('Desvio-padrao: {} m'.format(round(DISCREP.std(),3)))
        for result in RESULTADOS:
            feedback.pushInfo('{} ➜ {}'.format(dicionario[result],RESULTADOS[result]))

        
        # Criacao do arquivo html com os resultados
        arq = open(html_output, 'w')
        texto = '''
        <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
        <html>
        <head>
        <meta content="text/html; charset=ISO-8859-1"
        http-equiv="content-type">
        <title>MRE</title>
        </head>
        <body  bgcolor="#e5e9a6">
        <div style="text-align: center;"><span
        style="font-weight: bold; text-decoration: underline;">M&Eacute;TODO
        DOS
        RET&Acirc;NGULOS EQUIVALENTES</span><br>
        </div>
        <br>
        <span style="font-weight: bold;">1. Camada de Refer&ecirc;ncia</span><br>
        &nbsp;&nbsp;&nbsp; a. nome: {}<br>
        &nbsp;&nbsp;&nbsp; b. total de fei&ccedil;&otilde;es: {}<br>
        <br>
        <span style="font-weight: bold;">2. Camada de Teste</span><br>
        &nbsp;&nbsp;&nbsp; a. nome: {}<br>
        &nbsp;&nbsp;&nbsp; b. total de fei&ccedil;&otilde;es: {}<br>
        <br>
        <span style="font-weight: bold;">3. Relat&oacute;rio</span><br>
        &nbsp;&nbsp;&nbsp; a. Comprimento total relacionado (m): {}<br>
        &nbsp;&nbsp;&nbsp; b. m&eacute;dia ponderada das discrep&acirc;ncias (m): {}<br>
        &nbsp;&nbsp;&nbsp; c. REMQ ponderado (m): {}<br>
        &nbsp;&nbsp;&nbsp; d. discrep&acirc;ncia m&aacute;xima: {}<br>
        &nbsp;&nbsp;&nbsp; e. discrep&acirc;ncia m&iacute;nima: {}<br>
        &nbsp;&nbsp;&nbsp; f. <span style="font-weight: bold;">PEC-PCD</span>:<br>'''.format(self.str2HTML(ref.sourceName()), ref.featureCount(), self.str2HTML(teste.sourceName()), teste.featureCount(), '{:.4f}'.format(COMPR.sum()), '{:.4f}'.format(media_Pond), '{:.4f}'.format(EMQ), '{:.4f}'.format(max(DISCREP)),'{:.4f}'.format(min(DISCREP)))
        
        texto += '''<table style="text-align: left; width: 100%;" border="1"
        cellpadding="2" cellspacing="2">
        <tbody>
        <tr>''' 
        
        for escala in Escalas:
            texto += '    <td style="text-align: center; font-weight: bold;">{}</td>'.format(dicionario[escala])
        texto +='''
        </tr>
        <tr>'''
        
        for escala in Escalas:
            texto += '    <td style="text-align: center;">{}</td>'.format(RESULTADOS[escala])
        texto +='''
        </tr>
        </tbody>
        </table>
        <br>
        <br>
        <hr>
        <address><font size="+l">Leandro Fran&ccedil;a
        2022<br>
        Eng. Cart&oacute;grafo<br>
        email: geoleandro.franca@gmail.com<br>
        </font>
        </address>
        </body>
        </html>'''
        arq.write(texto)
        arq.close()
        
        feedback.pushInfo('Operação finalizada com sucesso!')
        feedback.pushInfo('Leandro França - Eng Cart')
        return {self.OUTPUT: dest_id,
                self.HTML: html_output}
