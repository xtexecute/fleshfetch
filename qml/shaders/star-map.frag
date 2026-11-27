#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float time;
    float glow;
    vec3 stroke0;
    vec3 stroke1;
    vec3 stroke2;
    vec3 stroke3;
};
layout(binding = 1) uniform sampler2D source;
layout(binding = 2) uniform sampler2D stars;
layout(binding = 3) uniform sampler2D halo;
layout(binding = 4) uniform sampler2D traits;

float lightWave(vec3 stroke,vec2 uv) {
    if (stroke.z>=1.0) return 0.0;
    float d=distance(uv,stroke.xy)-stroke.z*.85;
    return exp(-d*d/.009)*pow(1.0-stroke.z,1.3)*smoothstep(0.0,.055,stroke.z);
}

void main() {
    vec2 uv=qt_TexCoord0;
    float body=texture(source,uv).a;
    if (body<.001) { fragColor=vec4(0); return; }
    vec3 data=texture(traits,uv).rgb;
    float amplitude=glow*(.0015+.010*data.b);
    vec2 drift=vec2(sin(uv.y*19.0+uv.x*7.0+time*1.4),
                    cos(uv.x*17.0-uv.y*9.0-time*1.1))*amplitude;
    vec2 q=uv+drift;
    vec2 grid=(floor(q*112.0)+0.5)/112.0;
    vec2 starUv=mix(grid,q,min(1.0,glow*4.0));
    vec4 chart=texture(stars,starUv);
    vec4 bloom=texture(halo,q);
    data=texture(traits,q).rgb;
    float twinkle=mix(1.0,.77+.23*sin(time*(1.0+data.r*.8)+data.r*6.283),data.g);
    float wave=min(1.6,lightWave(stroke0,uv)+lightWave(stroke1,uv)
                        +lightWave(stroke2,uv)+lightWave(stroke3,uv));
    float gain=twinkle*(1.20+glow*.85+wave*1.4);
    float soft=.32+glow*1.6+wave*1.8;
    vec3 color=chart.rgb*gain+bloom.rgb*soft;
    float alpha=clamp(chart.a*gain+bloom.a*soft,0.0,1.0)*body;
    fragColor=vec4(min(color*body,vec3(alpha)),alpha)*qt_Opacity;
}
