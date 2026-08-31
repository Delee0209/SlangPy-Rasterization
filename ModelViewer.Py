import slangpy as spy
import numpy as np
import trimesh as tri

from dataclasses import dataclass
from App import *

class Vertex:
    def __init__(self,
                 position: list = [0, 0, 0],
                 normal: list = [0, 1, 0],
                 color: list = [0, 0, 0],
                 uv: list = [0, 0]):
        self.position = position
        self.normal = normal
        self.color = color
        self.uv = uv

    def flatten(self):
        return self.position + self.normal + self.color + self.uv
    
    def size(self):
        return len(self.flatten()) * 4
    
class G_buffer:
    def __init__(self,
                 device: spy.Device,
                 width: int,
                 height: int,
                 position_format: spy.Format,
                 albedo_format: spy.Format,
                 normal_format: spy.Format,
                 depth_format: spy.Format):
        self.device = device
        self.width, self.height = -1, -1
        self.clear_value = spy.float4(0.0)
        self.depth_clear_value = 1.0
        # texture formats
        self.position_format = position_format
        self.albedo_format = albedo_format
        self.normal_format = normal_format
        self.depth_format = depth_format
        # textures
        self.position_texture = None
        self.albedo_texture = None
        self.normal_texture = None
        self.depth_texture = None
        
        self.prepare(width, height)

    def prepare(self, width, height):
        if self.width != width or self.height != height:
            self.width, self.height = width, height
            self.position_texture = self.device.create_texture(format = self.position_format,
                                                               width = self.width,
                                                               height = self.height,
                                                               mip_count = 1,
                                                               usage = spy.TextureUsage.shader_resource | spy.TextureUsage.unordered_access | spy.TextureUsage.render_target,
                                                               label = "position")
            self.albedo_texture = self.device.create_texture(format = self.albedo_format,
                                                            width = self.width,
                                                            height = self.height,
                                                            mip_count = 1,
                                                            usage = spy.TextureUsage.shader_resource | spy.TextureUsage.unordered_access | spy.TextureUsage.render_target,
                                                            label = "albedo")
            self.normal_texture = self.device.create_texture(format = self.normal_format,
                                                             width = self.width,
                                                             height = self.height,
                                                             mip_count = 1,
                                                             usage = spy.TextureUsage.shader_resource | spy.TextureUsage.unordered_access | spy.TextureUsage.render_target,
                                                             label = "normal")
            self.depth_texture = self.device.create_texture(format = self.depth_format,
                                                            width = self.width,
                                                            height = self.height,
                                                            mip_count = 1,
                                                            usage = spy.TextureUsage.shader_resource | spy.TextureUsage.unordered_access | spy.TextureUsage.depth_stencil,
                                                            label = "depth",)
            
    def render_target_format(self):
        return [{"format": self.position_format}, 
                {"format": self.albedo_format}, 
                {"format": self.normal_format}]
    
    def color_attachments(self):
        return [{"view": self.position_texture.create_view({}),
                 "clear_value": self.clear_value},
                {"view": self.albedo_texture.create_view({}),
                 "clear_value": self.clear_value},
                {"view": self.normal_texture.create_view({}),
                 "clear_value": self.clear_value},]
        
    def depth_attachment(self):
        return {"view": self.depth_texture.create_view({}),
                "depth_load_op": spy.LoadOp.clear,
                "depth_store_op": spy.StoreOp.dont_care,
                "depth_clear_value": self.depth_clear_value}
    
    def depth_stencil(self):
        return {"format": self.depth_format,
                "depth_test_enable": True,
                "depth_write_enable": True,
                "depth_func": spy.ComparisonFunc.less,
                "stencil_enable": False}

    def bind(self, cursor: spy.ShaderCursor):
        cursor["position"] = self.position_texture
        cursor["albedo"] = self.albedo_texture
        cursor["normal"] = self.normal_texture
        cursor["depth"] = self.depth_texture

class ModelViewer:
    def __init__(self, width: int = 800, height: int = 800, clear_value: spy.float3 = spy.float3(0.0)):
        self.app = App(title = "ModelViewer", 
                       resizable = True, 
                       gui = False, 
                       width = width, 
                       height = height,
                       backend = spy.DeviceType.vulkan)
        self.width, self.height = width, height
        self.clear_value = spy.float4(clear_value, 1.0)

        self.timer = spy.Timer()
        self.device: spy.Device = self.app.device

        self.app.render = self.render
        self.app.external_resize = self.on_resize

        self.frame_number = 0

    def triangle(self):
        self.vertices = [Vertex([ 0.0,  0.5,  0.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0]),
                         Vertex([ 0.5, -0.5,  0.0], [0.0, 1.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0]),
                         Vertex([-0.5, -0.5,  0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0])]
        self.indices = [0, 1, 2]

    def quad(self):
        self.vertices = [Vertex([-0.5, -0.5,  0.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0]),
                         Vertex([ 0.5, -0.5,  0.0], [0.0, 1.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0]),
                         Vertex([ 0.5,  0.5,  0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0]),
                         Vertex([-0.5,  0.5,  0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 1.0], [0.0, 0.0])]
        self.indices = [[0, 1, 2],
                        [2, 3, 0]]
        
    def quads(self):
        self.vertices = [Vertex([-0.5, -0.5,  0.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0]),
                         Vertex([ 0.5, -0.5,  0.0], [0.0, 1.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0]),
                         Vertex([ 0.5,  0.5,  0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0]),
                         Vertex([-0.5,  0.5,  0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 1.0], [0.0, 0.0]),
                         Vertex([-0.5, -0.5, -0.5], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0]),
                         Vertex([ 0.5, -0.5, -0.5], [0.0, 1.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0]),
                         Vertex([ 0.5,  0.5, -0.5], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0]),
                         Vertex([-0.5,  0.5, -0.5], [0.0, 1.0, 0.0], [1.0, 1.0, 1.0], [0.0, 0.0])]
        self.indices = [[0, 1, 2],
                        [2, 3, 0],
                        [4, 5, 6],
                        [6, 7, 4]]
        
    def load_OBJ(self, file):
        model = tri.load(file)
        self.vertices = [Vertex(model.vertices[i].tolist(), model.vertex_normals[i].tolist(), [1.0, 1.0, 1.0], [0.0, 0.0]) for i in range(len(model.vertices))]
        self.indices = model.faces
    
    def load_GLTF(file):
        pass

    def prepare(self):
        vertex_data = np.array([vertex.flatten() for vertex in self.vertices], dtype = np.float32).flatten()
        index_data = np.array(self.indices, dtype = np.uint32).flatten()

        self.vertex_buffer = self.device.create_buffer(usage = spy.BufferUsage.vertex_buffer | spy.BufferUsage.shader_resource,
                                                       label = "vertex_buffer",
                                                       data = vertex_data)
        self.index_buffer = self.device.create_buffer(usage = spy.BufferUsage.index_buffer | spy.BufferUsage.shader_resource,
                                                      label = "index_buffer",
                                                      data = index_data)

        self.input_layout = self.device.create_input_layout(input_elements = [{"semantic_name" : "POSITION",
                                                                               "semantic_index" : 0,
                                                                               "format" : spy.Format.rgb32_float,
                                                                               "offset" : 0},
                                                                              {"semantic_name" : "NORMAL",
                                                                               "semantic_index" : 0,
                                                                               "format" : spy.Format.rgb32_float,
                                                                               "offset" : 12},
                                                                              {"semantic_name" : "COLOR",
                                                                               "semantic_index" : 0,
                                                                               "format" : spy.Format.rgb32_float,
                                                                               "offset" : 24},
                                                                              {"semantic_name" : "UV",
                                                                               "semantic_index" : 0,
                                                                               "format" : spy.Format.rg32_float,
                                                                               "offset" : 36}],
                                                            vertex_streams = [{"stride": Vertex().size()}])
        
        self.sampler = self.device.create_sampler(min_filter = spy.TextureFilteringMode.linear,
                                                  mag_filter = spy.TextureFilteringMode.linear,
                                                  address_u = spy.TextureAddressingMode.wrap,
                                                  address_v = spy.TextureAddressingMode.wrap)

        self.rasterizer = spy.RasterizerDesc({"cull_mode": spy.CullMode.none})

        self.position_format = spy.Format.rgba32_float
        self.albedo_format = spy.Format.rgba32_float
        self.normal_format = spy.Format.rgba32_float
        self.depth_format = spy.Format.d32_float

        self.g_buffer = G_buffer(self.device, self.width, self.height, self.position_format, self.albedo_format, self.normal_format, self.depth_format)

        self.rasterizer_program = self.device.load_program("shaders/Rasterizer.slang", ["vertex_main", "fragment_main"])
        
        self.render_pipeline = self.device.create_render_pipeline(program = self.rasterizer_program,
                                                                  input_layout = self.input_layout,
                                                                  targets = self.g_buffer.render_target_format(),
                                                                  depth_stencil = self.g_buffer.depth_stencil(),
                                                                  rasterizer = self.rasterizer)
        
        self.shading_program = self.device.load_program("shaders/shading.slang", entry_point_names = ["lighting"])

        self.compute_pipeline = self.device.create_compute_pipeline(self.shading_program)

    def update_uniform(self):
        time = self.timer.elapsed_s()
        self.model = spy.math.rotate(spy.float4x4.identity(), time * spy.math.radians(45.0), spy.float3(0.0, 0.0, 1.0))
        self.view = spy.math.matrix_from_look_at(spy.float3(2.0, 2.0, 2.0), spy.float3(0.0, 0.0, 0.0), spy.float3(0.0, 0.0, 1.0))
        self.projection = spy.math.perspective(spy.math.radians(40.0), self.app.width / self.app.height, 0.1, 10.0)
    
    def bind(self, cursor: spy.ShaderCursor):
        cursor["model"] = self.model
        cursor["view"] = self.view
        cursor["projection"] = self.projection
        cursor["frame_number"] = self.frame_number

    def render(self, app: App):
        self.frame_number += 1
        command_encoder = app.command_encoder
        render_texture = app.frame
        render_pass = {"color_attachments": self.g_buffer.color_attachments(),
                       "depth_stencil_attachment": self.g_buffer.depth_attachment()}
        self.update_uniform()
        # rasterization pass
        with command_encoder.begin_render_pass(render_pass) as pass_encoder:
            shader = pass_encoder.bind_pipeline(self.render_pipeline)
            cursor = spy.ShaderCursor(shader)
            self.bind(cursor.ubo)
            pass_encoder.set_render_state({"viewports" : [spy.Viewport.from_size(self.width, self.height)],
                                           "scissor_rects" : [spy.ScissorRect.from_size(self.width, self.height)],
                                           "vertex_buffers" : [self.vertex_buffer],
                                           "index_buffer" : self.index_buffer,
                                           "index_format" : spy.IndexFormat.uint32})
            # pass_encoder.draw({"vertex_count": len(self.vertices)})
            pass_encoder.draw_indexed({"vertex_count": len(self.indices) * 3})
        # lighting pass
        with command_encoder.begin_compute_pass() as pass_encoder:
            shader_object = pass_encoder.bind_pipeline(self.compute_pipeline)
            cursor = spy.ShaderCursor(shader_object)
            self.g_buffer.bind(cursor.g_buffer)
            cursor.sampler = self.sampler
            cursor.frame = render_texture
            self.bind(cursor.ubo)
            pass_encoder.dispatch(thread_count = [self.width, self.height, 1])

    def on_resize(self, app: App):
        if self.width != app.width or self.height != app.height:
            self.width, self.height = app.width, app.height
            self.g_buffer.prepare(self.width, self.height)

    def run(self):
        # Prepare GPU resources.
        self.prepare()
        self.app.run()

# initialize ModelViewer - window, device...
viewer = ModelViewer()
# load mesh
viewer.load_OBJ("media/viking_room.obj")
# execute
viewer.run()