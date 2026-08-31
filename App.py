from pathlib import Path
from typing import Callable, Optional, Union
import slangpy as spy

class App:
    def __init__(self,
                 title: str = "App",
                 width: int = 800,
                 height: int = 800,
                 resizable: bool = False,
                 vsync: bool = True,
                 gui: bool = True,
                 debug: bool = True,
                 frame_format: spy.Format = spy.Format.rgba32_float,
                 display_format: spy.Format = spy.Format.undefined,
                 include: list[Union[str, Path]] = [],
                 backend: spy.DeviceType = spy.DeviceType.automatic):
        super().__init__()
        # create device
        self.debug = debug
        self.device = spy.create_device(type = backend, include_paths = include, enable_debug_layers = False)
        self.command_encoder: spy.CommandEncoder = None
        # create window
        self.width = width
        self.height = height
        self.window = spy.Window(width = width, height = height, title = title, resizable = resizable)
        # create surface
        self.vsync = vsync
        self.display_format = display_format
        self.surface = self.device.create_surface(self.window)
        self.surface.configure(width = width, height = height, vsync = vsync, format = self.display_format)
        # output frame image
        self.frame_format = frame_format
        self.frame: spy.Texture = None
        # parameters
        self.mouse_pos = spy.float2()
        # events
        self.window.on_keyboard_event = self.on_keyboard_event
        self.window.on_mouse_event = self.on_mouse_event
        self.window.on_resize = self.on_resize
        # hookable external inputs
        self.external_keyboard_event: Optional[Callable[['App', spy.KeyboardEvent], None]] = None
        self.external_mouse_event: Optional[Callable[['App', spy.MouseEvent], None]] = None
        self.external_resize: Optional[Callable[['App'], None]] = None
        # hookable functions
        self.precompute: Optional[Callable[['App'], None]] = None
        self.preprocess: Optional[Callable[['App'], None]] = None
        self.render: Optional[Callable[['App'], None]] = None
        self.postprocess: Optional[Callable[['App'], None]] = None
        # hookable gui
        self.gui = gui
        self.ui: spy.ui.Context = None
        self.screen: spy.ui.Screen = None
        if gui:
            self.ui = spy.ui.Context(self.device)
            self.screen = self.ui.screen
        self.ui_layout: Optional[Callable[['App'], None]] = None
        self.ui_update: Optional[Callable[['App'], None]] = None

    def on_keyboard_event(self, event: spy.KeyboardEvent):
        # gui keyboard inputs
        if self.gui and self.ui.handle_keyboard_event(event):
            return
        # default keyboard inputs
        if event.is_key_press():
            if event.key == spy.KeyCode.escape:
                self.window.close()
                return
            elif event.key == spy.KeyCode.key1:
                if self.frame:
                    spy.tev.show_async(self.frame)
            elif event.key == spy.KeyCode.key2:
                if self.frame:
                    bitmap = self.frame.to_bitmap()
                    bitmap.convert(spy.Bitmap.PixelFormat.rgb,
                                   spy.Bitmap.ComponentType.uint8,
                                   srgb_gamma = True,).write_async("captured/screenshot.png")
        # external keyboard inputs
        if self.external_keyboard_event:
            self.external_keyboard_event(self, event)

    def on_mouse_event(self, event: spy.MouseEvent):
        # gui mouse inputs
        if self.gui and self.ui.handle_mouse_event(event):
            return
        # default mouse inputs
        if event.type == spy.MouseEventType.move:
            self.mouse_pos = event.pos
        # external mouse inputs
        if self.external_mouse_event:
            self.external_mouse_event(self, event)

    def on_resize(self, width: int, height: int):
        self.device.wait()
        if width > 0 and height > 0:
            self.width = width
            self.height = height
            self.surface.configure(width = width, height = height, vsync = self.vsync)
        else:
            self.surface.unconfigure()
        # external resize operation
        if self.external_resize:
            self.external_resize(self)

    def process_event(self):
        if self.window.should_close():
            return False
        self.window.process_events()
        # initialize or resize frame texture
        if (self.frame == None 
            or self.frame.width != self.width 
            or self.frame.height != self.height):
            self.frame = self.device.create_texture(format = self.frame_format,
                                                    width = self.width,
                                                    height = self.height,
                                                    mip_count = 1,
                                                    usage = spy.TextureUsage.shader_resource | spy.TextureUsage.unordered_access | spy.TextureUsage.render_target,
                                                    label = "frame",)
        return True
    
    def present(self):
        if not self.surface.config:
            return
        display = self.surface.acquire_next_image()
        if not display:
            return
        if self.gui:
            self.ui.begin_frame(display.width, display.height)
        self.command_encoder.blit(display, self.frame)
        self.command_encoder.set_texture_state(display, spy.ResourceState.present)
        if self.gui:
            self.ui.end_frame(display, self.command_encoder)
        self.device.submit_command_buffer(self.command_encoder.finish())
        del display
        self.surface.present()

    def run(self): # a skeleton main loop can be filled via hookable functions
        if self.gui and self.ui_layout:
            self.ui_layout(self)
        if self.precompute:
            self.precompute(self)
        while self.process_event():
            if self.gui and self.ui_update:
                self.ui_update(self)
            self.command_encoder = self.device.create_command_encoder()
            if self.preprocess:
                self.preprocess(self)
            if self.render:
                self.render(self)
            if self.postprocess:
                self.postprocess(self)
            self.present()

    def direct_display(self, framebuffer): # directly display the framebuffer
        self.command_encoder = self.device.create_command_encoder()
        if (self.frame == None 
            or self.frame.width != framebuffer.shape[1]
            or self.frame.height != framebuffer.shape[0]):
            self.frame = self.device.create_texture(format = self.frame_format,
                                                    width = framebuffer.shape[1],
                                                    height = framebuffer.shape[0],
                                                    mip_count = 1,
                                                    usage =spy.TextureUsage.shader_resource | spy.TextureUsage.unordered_access | spy.TextureUsage.render_target,
                                                    label = "frame",)
        self.frame.copy_from_numpy(framebuffer)
        self.present()

    def device(self):
        return self.device

    def frame_size(self):
        return spy.float2(self.width, self.height)