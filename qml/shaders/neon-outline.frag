#version 440
layout(location=0) in vec2 qt_TexCoord0;
layout(location=0) out vec4 fragColor;
layout(std140,binding=0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float bodyWidth;
    float time;
    float energy;
    float pulse;
    float origin;
};
layout(binding=1) uniform sampler2D field;
void main() {
    vec3 data=texture(field,qt_TexCoord0).rgb;
    float d=(data.r-.5)*64.0*bodyWidth/256.0;
    float phase=data.g;
    float hue=.5+.5*sin(phase*6.283-time*.7);
    vec3 tint=mix(vec3(.14,.92,1),vec3(1,.19,.54),hue);
    float chase=pow(max(0.0,cos((phase-origin-pulse)*6.283)),24.0)*(1.0-pulse)*energy;
    float core=exp(-pow((d-1.0)/1.1,2.0));
    float bloom=exp(-pow((d-1.0)/6.5,2.0));
    float a=min(.94,(core*.85+bloom*.18)*(1.0+energy*.35+chase*2.0));
    tint=mix(tint,vec3(.82,1,1),core*(.4+chase*.5));
    fragColor=vec4(tint*a,a)*qt_Opacity;
}
