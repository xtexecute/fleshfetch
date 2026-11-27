#version 440
layout(location=0) in vec2 qt_TexCoord0;
layout(location=0) out vec4 fragColor;
layout(std140,binding=0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float time;
    float energy;
    vec4 blob0;vec4 blob1;vec4 blob2;vec4 blob3;vec4 blob4;
};
void accumulate(vec4 b,vec2 p,inout float f,inout float heat,inout vec2 slope) {
    vec2 d=p-b.xy;
    float h=max(0.0,1.0-dot(d,d)/(4.0*b.z*b.z)),a=h*h*h;
    f+=a;heat+=a*b.w;slope+=d*h*h/(4.0*b.z*b.z);
}
void main() {
    vec2 p=floor(qt_TexCoord0*vec2(76,132))+.5;
    float side=25.0-(p.y-17.0)*12.0/80.0;
    if(p.y<18.0 || p.y>101.0 || p.x<side+1.0 || p.x>75.0-side) { fragColor=vec4(0);return; }
    float f=0,heat=0;vec2 slope=vec2(0);
    accumulate(blob0,p,f,heat,slope);accumulate(blob1,p,f,heat,slope);accumulate(blob2,p,f,heat,slope);
    accumulate(blob3,p,f,heat,slope);accumulate(blob4,p,f,heat,slope);
    heat/=max(.001,f);
    float wax=smoothstep(.41,.46,f);
    vec3 n=normalize(vec3(slope*80.0,.7));
    float key=max(0.0,dot(n,normalize(vec3(-.5,-.6,.8))));
    vec3 color=mix(vec3(.43,.035,.15),vec3(.99,.40,.16),heat)*(.6+key*.45);
    color+=vec3(.95,.55,.23)*pow(max(0.0,dot(n,normalize(vec3(-.4,-.5,1)))),22.0)*.45;
    float glow=exp(-pow((p.y-100.0)/17.0,2.0));
    vec3 glass=vec3(.08,.025,.08)+vec3(.50,.16,.065)*glow*(.6+energy*.4);
    glass+=vec3(.30,.055,.085)*min(.9,f)*.13;
    fragColor=vec4(clamp(mix(glass,color,wax),0.0,1.0)*.98,.98)*qt_Opacity;
}
