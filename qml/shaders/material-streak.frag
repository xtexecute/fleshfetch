#version 440
layout(location=0) in vec2 qt_TexCoord0;
layout(location=0) out vec4 fragColor;
layout(std140,binding=0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float fill;
    float time;
    float energy;
    float material;
    float roundClip;
    vec2 viewport;
};
float hash(vec2 p) { return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }
void main() {
    vec2 p=floor(qt_TexCoord0*viewport)+.5;
    vec2 circle=(p/viewport-.5)*2.0;
    if(roundClip>.5 && dot(circle,circle)>1.0) { fragColor=vec4(0);return; }
    float top=viewport.y*(1.0-(roundClip>.5 ? .96 : .84)*clamp(fill/100.0,0.0,1.0));
    float wave=material>.5 && material<1.5 ? 2.0*sin(p.x*.051)+sin(p.x*.13)
        : 1.5*sin(p.x*.04+time)+sin(p.x*.083-time*.6);
    float depth=p.y-top-wave;
    float a=smoothstep(-.5,.5,depth)*step(.001,fill);
    if(a==0.0) { fragColor=vec4(0); return; }
    vec3 color;
    float edge=exp(-max(0.0,depth)/1.4);
    if(material<.5) {
        float current=pow(.5+.5*sin(p.x*.034+depth*.022-time),6.0);
        color=mix(vec3(.035,.10,.17),vec3(.15,.055,.17),current);
        color+=mix(vec3(.10,.90,.92),vec3(.94,.18,.52),current)*edge*(.5+energy*.4);
    } else if(material<1.5) {
        float grain=hash(floor(p));
        color=mix(vec3(.49,.64,.73),vec3(.85,.91,.90),exp(-max(0.0,depth)/28.0));
        color+=vec3(.1)*step(.93,grain)*(.25+.75*exp(-max(0.0,depth)/18.0));
        color+=vec3(.08,.10,.09)*edge;
    } else {
        float fold=.5+.5*sin(p.x*.042+sin(depth*.045-time*.5)*1.8+time*.35);
        color=mix(vec3(.29,.06,.15),vec3(.65,.20,.15),fold*.6);
        color+=vec3(.83,.43,.16)*edge*(.5+energy*.25);
    }
    fragColor=vec4(color*a,a)*qt_Opacity;
}
