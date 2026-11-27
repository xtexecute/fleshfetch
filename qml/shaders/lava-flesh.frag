#version 440
layout(location=0) in vec2 qt_TexCoord0;
layout(location=0) out vec4 fragColor;
layout(std140,binding=0) uniform buf { mat4 qt_Matrix;float qt_Opacity;float time;float energy;vec2 bodyOrigin; };
layout(binding=1) uniform sampler2D source;
void main() {
    vec2 uv=qt_TexCoord0;
    vec2 p=uv*34.0+bodyOrigin;
    float side=25.0-(p.y-17.0)*12.0/80.0;
    if(p.y<19.0 || p.y>100.0 || p.x<side+1.0 || p.x>75.0-side) { fragColor=vec4(0);return; }
    uv+=vec2(sin(uv.y*11.0+time),cos(uv.x*9.0-time*.8))*(.009+energy*.014);
    vec4 flesh=texture(source,uv);
    fragColor=flesh*qt_Opacity;
}
