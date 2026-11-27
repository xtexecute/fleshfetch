#version 440
layout(location=0) in vec2 qt_TexCoord0;
layout(location=0) out vec4 fragColor;
layout(std140,binding=0) uniform buf { mat4 qt_Matrix;float qt_Opacity;vec2 p0;vec2 p1;vec2 p2;vec2 p3; };
layout(binding=1) uniform sampler2D flesh;
void main() {
    vec2 p=qt_TexCoord0*vec2(128,136);
    vec2 a=p1-p0,b=p2-p0,c=p0-p1-p2+p3;
    vec2 uv=(p-vec2(20,24))/88.0;
    for(int i=0;i<6;++i) {
        vec2 e=p0+a*uv.x+b*uv.y+c*uv.x*uv.y-p;
        vec2 u=a+c*uv.y,v=b+c*uv.x;
        float det=u.x*v.y-u.y*v.x;
        if(abs(det)<1.0) { fragColor=vec4(0);return; }
        uv-=vec2(e.x*v.y-e.y*v.x,u.x*e.y-u.y*e.x)/det;
    }
    if(any(lessThan(uv,vec2(0))) || any(greaterThanEqual(uv,vec2(1)))) { fragColor=vec4(0);return; }
    fragColor=texture(flesh,uv)*qt_Opacity;
}
