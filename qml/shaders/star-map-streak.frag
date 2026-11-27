#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float fill;
    float time;
    float glow;
    vec2 viewport;
};
float hash(vec2 p) { return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }
void main() {
    vec2 p=qt_TexCoord0*viewport;
    float top=viewport.y*(1.0-.84*clamp(fill/100.0,0.0,1.0));
    float wave=2.0*sin(p.x*.035+time*.8)+sin(p.x*.073-time*.6);
    float depth=p.y-top-wave;
    float mask=smoothstep(-.5,.5,depth)*step(.001,fill);
    if (mask==0.0) { fragColor=vec4(0); return; }
    vec2 cell=floor((p+vec2(sin(time*.2)*3,-time*1.4))/3.0);
    float seed=hash(cell);
    vec2 local=fract((p+vec2(sin(time*.2)*3,-time*1.4))/3.0);
    float point=step(.935,seed)*step(.35,local.x)*step(local.x,.69)*step(.35,local.y)*step(local.y,.69);
    float blink=.55+.45*sin(time*(.6+seed)+seed*27.0);
    vec3 color=vec3(.035,.064,.11);
    color+=mix(vec3(.32,.66,.81),vec3(.88,.75,.46),step(.975,seed))*point*blink*(.6+glow*.5);
    float edge=exp(-max(depth,0.0)/1.3);
    color+=vec3(.12,.31,.40)*edge;
    fragColor=vec4(color*mask,mask*.88)*qt_Opacity;
}
