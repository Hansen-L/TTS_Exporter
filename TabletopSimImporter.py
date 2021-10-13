import bpy
import requests
import re
import os
import cgi
import sys
import json
from math import radians
from mathutils import Euler

sys.path.append('/Applications/Blender.app/Contents/Resources/2.93/python/bin')
import wget



class CustomModel():
    def __init__(self, mesh_url, diffuse_url, transform, color_diffuse):
        self.mesh_url = mesh_url
        self.diffuse_url = diffuse_url
        self.transform = transform
        self.color_diffuse = color_diffuse

        
class Builder():
    savepath = '/Users/hansen/Desktop/hackdays/'

    # Download file, returns path
    def download_file(self, url):
        response = requests.get(url, allow_redirects=True)

        # Parse header for filename
        if response.headers.get('content-disposition'):
            value, params = cgi.parse_header(response.headers.get('content-disposition'))
            filename = params['filename']
        else:
            filename = wget.detect_filename(response.url).replace('|', '_')

        filepath = Builder.savepath + filename
        open(filepath, 'wb').write(response.content)

        return filepath
    
    def set_transform(self, object, transform):
        bpy.ops.transform.translate(value=(transform.posx, transform.posy, transform.posz))
        bpy.ops.transform.resize(value=(transform.scalex, transform.scaley, transform.scalez))
        object.rotation_euler = Euler((radians(transform.rotx), radians(transform.roty), radians(transform.rotz)), 'XYZ')

    def set_color_diffuse(self, object, color_diffuse):
        mat = bpy.data.materials.new("New_Mat")
        mat.diffuse_color = (color_diffuse.r, color_diffuse.g, color_diffuse.b, 1)
        object.active_material = mat

    def build_custom_model(self, custom_model):
        #download mesh 
        mesh_path = self.download_file(custom_model.mesh_url)

        #import mesh
        bpy.ops.import_scene.obj(filepath=mesh_path)

        #select imported object
        imported_object = bpy.context.selected_objects[0]
        
        #download diffuse, create material with texture
        if custom_model.diffuse_url:
            diffuse_path = self.download_file(custom_model.diffuse_url)
        
            mat = bpy.data.materials.new(name="New_Mat")
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes["Principled BSDF"]
            texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')
            texImage.image = bpy.data.images.load(diffuse_path)
            mat.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])

            # Assign it to object
            if imported_object.data.materials:
                imported_object.data.materials[0] = mat
            else:
                imported_object.data.materials.append(mat)
        #If no texture file, set color
        else:
            print(imported_object.active_material)
            self.set_color_diffuse(imported_object, custom_model.color_diffuse)
            
        #set transform
        self.set_transform(imported_object, custom_model.transform)
        #delete file
        #os.remove(mesh_path)





##############################################

# Python program to read a json file of Tabletop Simulator saves
class Transform():
    def __init__(self, posx=0, posy=0, posz=0, rotx=0, roty=0, rotz=0, scalex=1, scaley=1, scalez=1):
        self.posx = posx
        self.posy = posy
        self.posz = posz
        self.rotx = rotx
        self.roty = roty
        self.rotz = rotz
        self.scalex = scalex
        self.scaley = scaley
        self.scalez = scalez
        
class ColorDiffuse():
    def __init__(self, r=1, g=1, b=1):
        self.r = r
        self.g = g
        self.b = b

def parse_tts_json(json_path, builder):
    # TODO: Iterate through a list of JSON files.
    # f = open('tts_agricola.json',)
    # f = open('tts_agricola_edit.json',)
    f = open(json_path)
     
    # returns JSON object as
    # a dictionary
    data = json.load(f)

    gameName = data['GameMode']
    print(gameName)

    # Iterating through the objects in the scene
    for gameObject in data['ObjectStates']:
        if not gameObject: continue
        
        transform_holder = Transform()
        color_diffuse_holder = ColorDiffuse()

        # Extract all of the relevant information from each object in the scene
        GUID = gameObject.get('GUID')

        # TODO: Do we need to handle differently based on name? 
        # Object types I've seen so far: Custom_Board, Custom_Model, Custom_Model_Stack, Card, DeckCustom.
        # I've also found a type called HandTrigger and I'm not sure what it is or if we need to include it.
        objectType = gameObject.get('Name')
        print(gameObject)
        transform = gameObject.get('Transform')
        print(transform)
        transform_holder.posx = transform.get('posX')
        transform_holder.posy = transform.get('posY')
        transform_holder.posz = transform.get('posZ')
        transform_holder.rotx = transform.get('rotX')
        transform_holder.roty = transform.get('rotY')
        transform_holder.rotz = transform.get('rotZ')
        transform_holder.scalex = transform.get('scaleX')
        transform_holder.scaley = transform.get('scaleY')
        transform_holder.scalez = transform.get('scaleZ')

        colorDiffuse = gameObject.get('ColorDiffuse')
        color_diffuse_holder.r = colorDiffuse.get('r')
        color_diffuse_holder.g = colorDiffuse.get('g')
        color_diffuse_holder.b = colorDiffuse.get('b')

        # The following is only included in the "Custom_Board" object type.
        if (objectType == "Custom_Board"):
            customImage = gameObject.get('CustomImage')
            imageURL = customImage.get('ImageURL')
            imageScalar = customImage.get('ImageScalar') # TODO: What is scalar vs. width scale here?
            widthScale = customImage.get('WidthScale')

        # The following is only included in "Custom_Model" and "Custom_Model_Stack" object types.
        if (objectType == "Custom_Model") or (objectType == "Custom_Model_Stack"): 
            customMesh = gameObject.get('CustomMesh')
            meshURL = customMesh.get('MeshURL')
            textureURL = customMesh.get('DiffuseURL') # textureURL will be 'None' for objects without a texture.
            
            print(meshURL)
            custom_model = CustomModel(meshURL, textureURL, transform_holder, color_diffuse_holder)
            builder.build_custom_model(custom_model)
            # TODO: Handle Custom_Model_Stack?

        # The following is only included in the "Card" object type.
        if (objectType == "Card"):
            cardID = gameObject.get('CardID')
            # Each CustomDeck has a single key that is effectively its ID.
            customDeck = gameObject.get('CustomDeck')
            deckID = list(customDeck.keys())[0]
            deck = list(customDeck.values())[0]

            # Extract the card number from its ID, which includes both the deck id and card number.
            deckIDLength = len(deckID)
            stringCardID = str(cardID)
            cardIDLength = len(str(cardID))
            cardNumber = stringCardID[deckIDLength:cardIDLength]

            cardFaceURL = deck.get('FaceURL')
            cardBackURL = deck.get('BackURL')
            cardWidth = deck.get('NumWidth')
            cardHeight = deck.get('NumHeight')

        # The following is only included in the "DeckCustom" object type.
        # TODO: Pull in each Card's DeskCustom, get the ID for the deck, then pull out each card's ID by removing the deck ID from the beginning of it.
        if (objectType == "DeckCustom") or (objectType == "Deck"):
            deckIDs = gameObject.get('DeckIDs')

            # Each CustomDeck has a single key that is effectively its ID.
            customDeck = gameObject.get('CustomDeck')
            deckID = list(customDeck.keys())[0]
            deck = list(customDeck.values())[0]

            cardFaceURL = deck.get('FaceURL')
            cardBackURL = deck.get('BackURL')
            cardWidth = deck.get('NumWidth')
            cardHeight = deck.get('NumHeight')

    # Closing file
    f.close()

##############################################



#print(sys.exec_prefix)
#transform = Transform(-27.88947, 1.48692358, 8.511686, 358.470367, 359.980927,1.84674513,1.25, 1.25, 1.25)
#test_model = CustomModel('https://www.dropbox.com/s/ht66xc0qb2b8wv8/Tokaido.Board.obj?dl=1','https://i.imgur.com/Vot1gxK.jpg', transform)
#builder = Builder()
#builder.build_custom_model(test_model)
#builder.build_custom_model(test_model)


json_path = ('/Users/hansen/Desktop/agricola.json')
builder = Builder()
parse_tts_json(json_path, builder)

#bpy.ops.import_scene.obj(filepath='/Users/hansen/Desktop/hackdays/Tokaido.Board.obj')