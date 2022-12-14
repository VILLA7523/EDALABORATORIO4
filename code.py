from PIL import Image # Libreria que agrega soporte para abrir, manipular y guardar muchos formatos de archivo de imagen diferentes
import argparse

class Color(object): # Clase Color: Almacena atributos RGB de un color
    def __init__(self, red=0, green=0, blue=0): # Constructor
        self.red = red
        self.green = green
        self.blue = blue

class NodeOctree(object): # Clase Nodo del Octree
    def __init__(self, level, parent): # Constructor
        self.color = Color(0, 0, 0)
        self.cntPixel = 0
        self.indPaleta = 0
        self.children = [None for _ in range(8)] # Ocho hijos del octree
        if level < Octree.MAX_DEPTH - 1: # añade un nodo al nivel actual
            parent.AddNodeByLevel(level, self)
    def getNodesLeaf(self): # Obtener todos los nodos hoja
        nodesLeaf = []
        for i in range(8):
            if self.children[i]:
                if self.children[i].cntPixel > 0:
                    nodesLeaf.append(self.children[i])
                else:
                    nodesLeaf.extend(self.children[i].getNodesLeaf())
        return nodesLeaf
    def getCntPixelNodes(self): # Obtener una suma de la cantidad de píxeles para el nodo y sus hijos
        sum = self.cntPixel
        for i in range(8):
            if self.children[i]:
                sum += self.children[i].cntPixel
        return sum
    def addColor(self, color, level, parent): # Añadir un color al arbol
        if level >= Octree.MAX_DEPTH:
            self.color.red += color.red
            self.color.green += color.green
            self.color.blue += color.blue
            self.cntPixel += 1
            return
        index = self.getColorLevel(color, level)
        if not self.children[index]:
            self.children[index] = NodeOctree(level, parent)
        self.children[index].addColor(color, level + 1, parent)
    def getIndPaleta(self, color, level): #  Obtiene el índice de paleta para color. Utiliza nivel para ir un nivel más allá si el nodo no es una hoja
        if self.cntPixel > 0:
            return self.indPaleta
        index = self.getColorLevel(color, level)
        if self.children[index]:
            return self.children[index].getIndPaleta(color, level + 1)
        else:
            for i in range(8): # Obtener el índice de paleta para el primer nodo hijo encontrado
                if self.children[i]:
                    return self.children[i].getIndPaleta(color, level + 1)
    def deleteLeaves(self): # Añade el recuento de píxeles y los canales de color de todos los hijos al nodo padre. Devuelve el número de hojas eliminadas
        ans = 0
        for i in range(8):
            node = self.children[i]
            if node:
                self.color.red += node.color.red
                self.color.green += node.color.green
                self.color.blue += node.color.blue
                self.cntPixel += node.cntPixel
                ans += 1
        return ans - 1
    def getColorLevel(self, color, level): # Obtener el índice de color para el siguiente nivel
        index = 0
        mask = 0x80 >> level
        if color.red & mask:
            index |= 4
        if color.green & mask:
            index |= 2
        if color.blue & mask:
            index |= 1
        return index
    def getColor(self): # Obtener el color medio
        return Color(
            self.color.red / self.cntPixel,
            self.color.green / self.cntPixel,
            self.color.blue / self.cntPixel)

class Octree(object): #  Clase Octree Quantizer
    MAX_DEPTH = 8 # Para limitar el número de niveles
    def __init__(self): # Constructor
        self.levels = {i: [] for i in range(Octree.MAX_DEPTH)}
        self.root = NodeOctree(0, self)
    def getLeaves(self): # Obtener todas las hojas
        return [node for node in self.root.getNodesLeaf()]
    def AddNodeByLevel(self, level, node): # Añadir nodo a los nodos en nivel
        self.levels[level].append(node)
    def addColor(self, color): # Añadir color al octree
        self.root.addColor(color, 0, self) # pasa el valor de self como `parent` para guardar los nodos en los niveles dict
    def constructPaleta(self, color_count):
        palette = []
        indPaleta = 0
        leaf_count = len(self.getLeaves())
        # Reduce nodos. Se pueden reducir hasta 8 hojas y la paleta tendrá solo 248 colores (en el peor de los casos) en lugar de los 256 colores esperados
        for level in range(Octree.MAX_DEPTH - 1, -1, -1):
            if self.levels[level]:
                for node in self.levels[level]:
                    leaf_count -= node.deleteLeaves()
                    if leaf_count <= color_count:
                        break
                if leaf_count <= color_count:
                    break
                self.levels[level] = []
        for node in self.getLeaves(): # Construir la paleta
            if indPaleta >= color_count:
                break
            if node.cntPixel > 0:
                palette.append(node.getColor())
            node.indPaleta = indPaleta
            indPaleta += 1
        return palette
    def getIndPaleta(self, color): #  Obtener el índice de la paleta para color
        return self.root.getIndPaleta(color, 0)

def main():
    parser = argparse.ArgumentParser(description="Octree_Quantizer") #establecer algoritmos
    parser.add_argument('input_file')
    
    args = vars(parser.parse_args())
    print(args)
    image = Image.open(args['input_file'])
    pixels = image.load()
    width, height = image.size
    octree = Octree() # Inicializando el octree
    octree_64 = Octree() # Inicializando el octree
    
    # Añadir los colores al octree
    for j in range(height):
        for i in range(width):
            color = Color(*pixels[i, j])
            octree.addColor(color)
            octree_64.addColor(color)
    
    ###################################### 256-bits ########################################33
    # 256 colores para una imagen de salida de 8 bits por pixel   
    palette_256 = octree.constructPaleta(256)
    
    # Crear paleta para 256 colores y guardar la paleta como archivo
    palette_256_image = Image.new('RGB', (16, 16))
    palette_256_pixels = palette_256_image.load()
    for i, color in enumerate(palette_256):
        palette_256_pixels[i % 16, i / 16] = (int(color.red), int (color.green), int (color.blue))
    
    #Estableciendo el nombre del archivo de salida(paleta)
    name = args['input_file'].split('.')
    name = name[0] + '_256_palette.' + name[1]
    palette_256_image.save('Img/' + name)
    
    # Guardar la imagen resultante
    out_image = Image.new('RGB', (width, height))
    out_pixels = out_image.load()
    for j in range(height):
        for i in range(width):
            index = octree.getIndPaleta(Color(*pixels[i, j])) 
            color = palette_256[index]
            out_pixels[i, j] = (int(color.red), int(color.green), int(color.blue))
    #Estableciendo el nombre del archivo de salida(paleta)
    name = args['input_file'].split('.')
    name = name[0] + '_256_ImageReduced.' + name[1]
    out_image.save('Img/' + name)
    
    ###################################### 64-bits ########################################33
    # 64 colores para una imagen de salida de 6 bits por pixel   
    palette_64 = octree_64.constructPaleta(64)
    
    # Crear paleta para 64 colores y guardar la paleta como archivo
    palette_64_image = Image.new('RGB', (8, 8))
    palette_64_pixels = palette_64_image.load()
    for i, color in enumerate(palette_64):
        palette_64_pixels[i % 8, i / 8] = (int(color.red), int (color.green), int (color.blue))
    
    #Estableciendo el nombre del archivo de salida(paleta)
    name = args['input_file'].split('.')
    name = name[0] + '_64_palette.' + name[1]
    palette_64_image.save('Img/' + name)
    
    # Guardar la imagen resultante
    out_image_64 = Image.new('RGB', (width, height))
    out_pixels_64 = out_image_64.load()
    for j in range(height):
        for i in range(width):
            index_64 = octree_64.getIndPaleta(Color(*pixels[i, j]))
            color = palette_64[index_64]
            out_pixels_64[i, j] = (int(color.red), int(color.green), int(color.blue))
    #Estableciendo el nombre del archivo de salida(paleta)
    name = args['input_file'].split('.')
    name = name[0] + '_64_ImageReduced.' + name[1]
    out_image_64.save('Img/' + name)

if __name__ == '__main__':
    main()
