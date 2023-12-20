"""
UVFX 

License: GPLv3
Author: Powerbyte7
Github: https://github.com/Powerbyte7/UV_FX
"""

import bpy
import bpy_extras.image_utils
import os
from bpy.types import Panel, Operator, PropertyGroup, UIList
from bpy.props import StringProperty, FloatVectorProperty, EnumProperty, PointerProperty

class UVFXlayer(PropertyGroup):
	name: bpy.props.StringProperty(
		name='Name',
		default="Footage",
		description='Footage Name'
	)
	
	uv_path: bpy.props.StringProperty(
		name='UV Path',
		default="//Template/UV1/",
		subtype='DIR_PATH',
		description='Directory of UV pass'
	)
	
	footage_path: bpy.props.StringProperty(
		name='Footage Path',
		default="//",
		subtype='DIR_PATH',
		description='Directory of footage'
	)
	
	uv_transform: bpy.props.StringProperty(
		name='UV Transform',
		description='Footage UV Transform Node',
		default="None"
	)
	
	uv_tile: bpy.props.StringProperty(
		name='UV Tile',
		description='Footage UV Tile Node',
		default="None"
	)
	
	blend_node: bpy.props.StringProperty(
		name='Blend Node',
		description='Blend Node For Footage',
		default="None",
	)
	
	node_tree: bpy.props.StringProperty(
		name='Node Tree',
		description='Node Tree For Custom Layers',
		default="None",
	)
	
	layer_types = [
		('COLOR', 'Color', 'Color footage'),
		('UV', 'UV', 'UV footage'),
		('MULTIPLY', 'Multiply', 'Multiply footage'),
		('ADD', 'Add', 'Additive footage'),
		('CUSTOM_NODE', 'Custom', 'Custom Node Group'),
		('CUSTOM_FOOTAGE_NODE', 'Custom+Footage', 'Custom Node Group With Footage'),
	]
	
	icons = {
		'COLOR': 'NODE_COMPOSITING',
		'UV': 'MOD_UVPROJECT',
		'MULTIPLY': 'OUTLINER_OB_LIGHT',
		'ADD': 'OUTLINER_OB_LIGHTPROBE',
	}
	
	type: bpy.props.EnumProperty(
		name="Footage Type",
		description="Footage Type",
		items=layer_types,
		default='UV',
	)

class UVFXoptions(PropertyGroup):
	
	layer_list: bpy.props.CollectionProperty(
		type=UVFXlayer
	)
	
	active_layer: bpy.props.IntProperty(
		default=0
	)
	
	render_output_path: bpy.props.StringProperty(
		name='Render output path',
		default="//Render/",
		subtype='DIR_PATH',
		description='Directory render data will be exported to'
	)

class UVFX_OT_layer_add(Operator):
	
	bl_idname = "uvfx.layer_slot_add"
	bl_label = "Adds layer slot"
	
	def execute(self, context):
		uvfx = context.scene.uvfx_options
		
		footage = uvfx.layer_list.add()
		footage.name = "New Footage"
		
		return {'FINISHED'}
	
	
class UVFX_OT_layer_remove(Operator):
	
	bl_idname = "uvfx.layer_slot_remove"
	bl_label = "Removes layer slot"
	
	def execute(self, context):
		uvfx = context.scene.uvfx_options
	
		active = uvfx.active_layer
		uvfx.layer_list.remove(active)
		
		# Might be smart to reconfigure after removal
		# bpy.ops.uvfx.configure_compositor()
		
		return {'FINISHED'}

class UGVFX_OT_configure_compositor(Operator):
	
	bl_idname = "uvfx.configure_compositor"
	bl_label = "Sets up nodetree"

	def get_image(self, path):
		image = None
		frame_duration = 0
		
		# List of compatible extensions
		image_extensions = ['.jpg', '.jpeg', '.png', '.exr']
		video_extensions = ['.mkv', '.mp4', '.webm', '.avi']
		
		# Iterate through directory entries
		for entry in os.scandir(path):
			if entry.is_dir():
				continue
			
			extension = os.path.splitext(entry.name)[1]
			
			if extension in image_extensions:
				image = bpy_extras.image_utils.load_image(imagepath=entry.name, dirname=path)
				image.source = 'SEQUENCE'
				frame_duration = len([x for x in os.scandir(path) if os.path.splitext(x.name)[1] == extension])
				
				if frame_duration == 1:
					image.source = 'FILE'
				break
				
			elif extension in video_extensions:
				image = bpy_extras.image_utils.load_image(imagepath=entry.name, dirname=path)
				image.source = 'MOVIE'
				frame_duration = image.frame_duration
				break
		
		return image, frame_duration
	
	def get_image_node(self, path):
		
		tree = bpy.context.scene.node_tree
		
		# Get image from path
		image, frame_duration = self.get_image(path)
		
		if image is None:
			return None
		
		# Create node
		node = tree.nodes.new(type='CompositorNodeImage')
		node.image = image
		
		# Set footage length
		node.frame_duration = frame_duration
		
		# Change node settings
		node.use_cyclic = True
		node.use_auto_refresh = True
		
		return node
	
	def compositor_setup(self, context):
		uvfx = context.scene.uvfx_options
		
		# Enable compositor
		scene = bpy.context.scene
		scene.use_nodes = True
		
		tree = scene.node_tree
		
		# Read and store current node state
		# This step can be skipped to reset all node data
		for layer in uvfx.layer_list:
			# Store previous node group tree
			try:
				layer.node_tree = tree.nodes[layer.blend_node].node_tree.name
				print(layer.node_tree)
			except (KeyError, AttributeError):
				pass
			
			# TODO
			# Store blend factor
			# Store UV transform
			# Store UV tiling
		
		# Clear nodes
		for node in tree.nodes:
			tree.nodes.remove(node)

		# Variable to set node offset
		x_offset = 0
		
		for layer in uvfx.layer_list:
			
			if layer.type == 'COLOR':
				# Add color input
				color_path = bpy.path.abspath(layer.footage_path)
				color_input_node = self.get_image_node(color_path)
				
				# Update loop state
				x_offset += 400
				last_node = color_input_node
			
			elif layer.type == 'MULTIPLY':
				# Add footage
				footage_path = bpy.path.abspath(layer.footage_path)
				footage_node = self.get_image_node(footage_path)
				footage_node.location = x_offset, -600
				
				# Add mix node
				multiply_node = tree.nodes.new(type='CompositorNodeGroup')
				multiply_node.node_tree = bpy.data.node_groups['Multiply']
				# multiply_node = tree.nodes.new(type='CompositorNodeMixRGB')
				# add_node.blend_type = 'MULTIPLY'
				multiply_node.inputs[0].default_value = 1.0
				multiply_node.location = x_offset+800, 0
				
				# Create links
				tree.links.new(last_node.outputs[0], multiply_node.inputs[1])
				tree.links.new(footage_node.outputs[0], multiply_node.inputs[2])
				last_node = multiply_node
				
				# Update loop state
				x_offset += 400
				last_node = multiply_node
				layer.blend_node = multiply_node.name
				
			elif layer.type == 'ADD':
				# Add footage
				footage_path = bpy.path.abspath(layer.footage_path)
				footage_node = self.get_image_node(footage_path)
				footage_node.location = x_offset, -600
				
				# Add mix node
				add_node = tree.nodes.new(type='CompositorNodeGroup')
				add_node.node_tree = bpy.data.node_groups['Add']
				# add_node = tree.nodes.new(type='CompositorNodeMixRGB')
				# add_node.blend_type = 'ADD'
				add_node.inputs[0].default_value = 1.0
				add_node.location = x_offset+800, 0
				
				# Make connections
				tree.links.new(last_node.outputs[0], add_node.inputs[1])
				tree.links.new(footage_node.outputs[0], add_node.inputs[2])
				last_node = add_node
				
				# Update loop state
				x_offset += 400
				last_node = add_node
				layer.blend_node = add_node.name

			elif layer.type == 'CUSTOM_NODE':

				# Add mix node
				custom_node = tree.nodes.new(type='CompositorNodeGroup')
				
				# Set node tree, sets copy of 'Custom' by default
				if layer.node_tree == "None":
					custom_node.node_tree = bpy.data.node_groups['Custom'].copy()
					layer.node_tree = custom_node.node_tree.name
				else:
					try:
						custom_node.node_tree =  bpy.data.node_groups[layer.node_tree]
					except KeyError as e:
						custom_node.node_tree = bpy.data.node_groups['Custom'].copy()
						layer.node_tree = custom_node.node_tree.name
						
				custom_node.location = x_offset+800, 0
				
				# Make connections
				tree.links.new(last_node.outputs[0], custom_node.inputs[1])
				
				# Update loop state
				x_offset += 400
				last_node = custom_node
				layer.blend_node = custom_node.name
			
			elif layer.type == 'CUSTOM_FOOTAGE_NODE':
				# Add footage
				footage_path = bpy.path.abspath(layer.footage_path)
				footage_node = self.get_image_node(footage_path)
				footage_node.location = x_offset, -600

				# Add mix node
				custom_node = tree.nodes.new(type='CompositorNodeGroup')
				
				# Set node tree, sets copy of 'CustomFootage' by default
				if layer.node_tree == "None":
					custom_node.node_tree = bpy.data.node_groups['CustomFootage'].copy()
					layer.node_tree = custom_node.node_tree.name
				else:
					try:
						custom_node.node_tree =  bpy.data.node_groups[layer.node_tree]
					except KeyError as e:
						custom_node.node_tree = bpy.data.node_groups['CustomFootage'].copy()
						layer.node_tree = custom_node.node_tree.name
						
				custom_node.location = x_offset+800, 0
				
				# Make connections
				tree.links.new(last_node.outputs[0], custom_node.inputs[1])
				tree.links.new(footage_node.outputs[0], custom_node.inputs[2])
				
				# Update loop state
				x_offset += 400
				last_node = custom_node
				layer.blend_node = custom_node.name
				
			elif layer.type == 'UV':
				# Add footage node
				footage_path = bpy.path.abspath(layer.footage_path)
				footage_node = self.get_image_node(footage_path)
				footage_node.location = x_offset, -100
				
				# Add UV node
				uv_path = bpy.path.abspath(layer.uv_path)
				uv_node = self.get_image_node(uv_path)
				uv_node.image.colorspace_settings.name = 'Non-Color'
				uv_node.location = x_offset, -600
				
				# Add UV transform nodes
				uv_transform_node = tree.nodes.new(type='CompositorNodeGroup')
				uv_transform_node.location = x_offset+200, -600
				uv_transform_node.node_tree = bpy.data.node_groups['UV transform']
				layer.uv_transform = uv_transform_node.name
				
				uv_tile_node = tree.nodes.new(type='CompositorNodeGroup')
				uv_tile_node.location = x_offset+200, -400
				uv_tile_node.node_tree = bpy.data.node_groups['UV tile']
				uv_tile_node.mute = True
				layer.uv_tile = uv_tile_node.name
				
				map_uv_node = tree.nodes.new(type='CompositorNodeMapUV')
				map_uv_node.location = x_offset+400, -300
				
				alpha_over_node = tree.nodes.new(type='CompositorNodeAlphaOver')
				alpha_over_node.location = x_offset+800, 0
				layer.blend_node = alpha_over_node.name
				
				# Make connections
				tree.links.new(footage_node.outputs[0], map_uv_node.inputs[0])
				tree.links.new(uv_node.outputs[0], uv_transform_node.inputs[0])
				tree.links.new(uv_transform_node.outputs[0], uv_tile_node.inputs[0])
				tree.links.new(uv_tile_node.outputs[0], map_uv_node.inputs[1])
				
				tree.links.new(last_node.outputs[0], alpha_over_node.inputs[1])
				tree.links.new(map_uv_node.outputs[0], alpha_over_node.inputs[2])
				
				# Update loop state
				x_offset += 400
				last_node = alpha_over_node
		
		x_offset += 400
		
		# Add outputs
		composite_node = tree.nodes.new(type='CompositorNodeComposite')
		composite_node.location = x_offset+400, 0
		viewer_node = tree.nodes.new(type='CompositorNodeViewer')
		viewer_node.location = x_offset+400, -300
		
		# Make final connections
		tree.links.new(last_node.outputs[0], composite_node.inputs[0])
		tree.links.new(last_node.outputs[0], viewer_node.inputs[0])
		
	def execute(self, context):
		self.compositor_setup(context)
		
		return {'FINISHED'}


class UVFX_PT_main_panel(Panel):
	bl_label = "UVFX Template Options"
	bl_idname = "UVFX_PT_main_panel"
	bl_space_type = "VIEW_3D" # "NODE_EDITOR"
	bl_region_type = "UI"
	bl_category = "UVFX"
	
	def draw(self,context):
		layout = self.layout
		scene = context.scene
		uvfx = bpy.context.scene.uvfx_options
		node_tree_nodes = context.scene.node_tree.nodes
		
		# Render button
		render = layout.operator("render.opengl", icon='VIEW_CAMERA', text="Render template")
		render.animation = True
		
		# Node setup button
		layout.operator("uvfx.configure_compositor", icon='NODETREE', text="Set up nodes")
		
		sub = layout.row(align=True)
		sub.prop(scene, "frame_start", text="Start")
		sub.prop(scene, "frame_end", text="End")
		
		# Template and render paths
		layout.prop(context.scene.render, 'filepath', text="Render output")
		
		# Custom footage slots
		row = layout.row()
		row.template_list("UVFX_UL_layer_list", "", uvfx, "layer_list", uvfx, "active_layer")
		
		col = row.column(align=True)
		col.operator("uvfx.layer_slot_add", icon='ADD', text="")
		
		# Remove layer (Removing base layer not allowed)
		if uvfx.active_layer != 0:
			col.operator("uvfx.layer_slot_remove", icon='REMOVE', text="")
		
		# Layer view
		active_layer = uvfx.layer_list[uvfx.active_layer]
		
		# Layer type
		layout.prop(active_layer, 'type', text="Layer Type")
		
		# Footage path
		if active_layer.type != 'CUSTOM_NODE':
			layout.prop(active_layer, 'footage_path', text="Footage")
		
		# UV path
		if active_layer.type == 'UV':
			layout.prop(active_layer, 'uv_path', text="UV")
		
		# Node tree selector
		if active_layer.type in ['CUSTOM_NODE', 'CUSTOM_FOOTAGE_NODE'] and active_layer.blend_node != "None":
			custom_node = node_tree_nodes[active_layer.blend_node]
			layout.prop(custom_node, 'node_tree', text="Node Group")		
		
		# UV transform settings
		if active_layer.uv_transform != "None":
			uv_transform_node = node_tree_nodes[active_layer.uv_transform]

			value_inputs = [socket for socket in uv_transform_node.inputs if self.show_socket_input(socket)]
			
			if value_inputs:
				layout.separator()
				layout.label(text="UV settings:")
				for socket in value_inputs:
					row = layout.row()
					socket.draw(
						context,
						row,
						uv_transform_node,
						socket.label if socket.label else socket.name,
					)
		
		# UV transform settings
		if active_layer.uv_tile != "None":
			uv_tile_node = node_tree_nodes[active_layer.uv_tile]
			
			layout.prop(uv_tile_node, 'mute', text='Enable Tiling', toggle=1, invert_checkbox=True)
		
		# Blending settings
		if active_layer.blend_node != "None":
			uv_tile_node = node_tree_nodes[active_layer.blend_node]
			
			value_inputs = [socket for socket in uv_tile_node.inputs if self.show_socket_input(socket)]
			
			if value_inputs:
				layout.separator()
				layout.label(text="Blending settings:")
				for socket in value_inputs:
					row = layout.row()
					socket.draw(
						context,
						row,
						uv_tile_node,
						socket.label if socket.label else socket.name,
					)
			
			layout.prop(uv_tile_node, 'mute', text='Disable layer', toggle=1)
			
	def show_socket_input(self, socket):
		return hasattr(socket, "draw") and socket.enabled and not socket.is_linked
			

class UVFX_UL_layer_list(UIList):

	def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
		ob = data
		ma = item.name
		
		if self.layout_type in {'DEFAULT', 'COMPACT'}:
			
			if ma:
				layout.prop(item, "name", text="", emboss=False, icon_value=icon)
			else:
				layout.label(text="", translate=False, icon_value=icon)
		
		elif self.layout_type == 'GRID':
			layout.alignment = 'CENTER'
			layout.label(text="", icon_value=icon)
		

classes = [
	UVFXlayer,
	UVFXoptions,
	UVFX_OT_layer_add,
	UVFX_OT_layer_remove,
	UGVFX_OT_configure_compositor,
	UVFX_UL_layer_list,
	UVFX_PT_main_panel
]
		
def register():
	for c in classes:
		bpy.utils.register_class(c)
		
	bpy.types.Scene.uvfx_options = bpy.props.PointerProperty(
		type=UVFXoptions)

def unregister():
	for c in classes:
		bpy.utils.unregister_class(c)
		
		
if __name__ == "__main__":
	register()