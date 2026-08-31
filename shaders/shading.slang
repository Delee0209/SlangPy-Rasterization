import common;

struct G_buffer
{
    Texture2D<float4> position;
    Texture2D<float4> albedo;
    Texture2D<float4> normal;
    Texture2D<float> depth;
}

struct SSAO
{
    float radius = 4.0;
}

RWTexture2D<float4> frame;
SamplerState sampler;
ParameterBlock<G_buffer> g_buffer;
ConstantBuffer<UniformBuffer> ubo;

static const float kernel_size = 64;
static const float radius = 0.075f;
static const float bias = 0.025f;

[shader("compute")]
void lighting(uint3 thread_id: SV_DispatchThreadID)
{
    uint2 pixel = thread_id.xy;
    uint2 dimension;
    frame.GetDimensions(dimension.x, dimension.y);
    if (any(pixel >= dimension))
    {
        return;
    }

    if (g_buffer.depth[pixel] >= 1.f)
    {
        frame[pixel] = float4(float3(0.f), 1.f);
        return;
    }

    float3 position = g_buffer.position[pixel].xyz;
    float3 normal = normalize(g_buffer.normal[pixel].xyz);

    RNG rng = RNG(pixel, ubo.frame_number);

    float3 randomVec = normalize(float3(rng.sample_1d() * 2.0 - 1.0, rng.sample_1d() * 2.0 - 1.0, rng.sample_1d()));
    float3 tangent = normalize(randomVec - normal * dot(randomVec, normal));
    float3 bitangent = cross(normal, tangent);
    float3x3 TBN = float3x3(tangent, bitangent, normal);

    float occlusion = 0.0;

    for (uint i = 0; i < kernel_size; i++)
    {
        float3 sampleDir = normalize(float3(rng.sample_1d() * 2.0 - 1.0, rng.sample_1d() * 2.0 - 1.0, rng.sample_1d()));
        float scale = (float)i / 64.0;
        scale = lerp(0.1, 1.0, scale * scale);
        float3 samplePos = position + mul(TBN, sampleDir) * radius * scale;

        float4 clip = mul(ubo.projection, float4(samplePos, 1.0));
        clip.xyz /= clip.w;
        float2 uv = clip.xy * 0.5 + 0.5;
        uv.y = 1.0 - uv.y;
        if (any(uv < 0.0) || any(uv > 1.0))
            continue;

        uint2 samplePixel = uint2(uv * dimension);
        float3 samplePosition = g_buffer.position[samplePixel].xyz;

        float rangeCheck = smoothstep(0.0, 1.0, radius / abs(position.z - samplePosition.z));

        occlusion += (samplePosition.z >= samplePos.z + bias ? 1.0 : 0.0) * rangeCheck;
    }

    occlusion = 1.0 - (occlusion / kernel_size);

    frame[pixel] =
        float4(occlusion.xxx, 1.0);
}
