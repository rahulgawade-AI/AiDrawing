from townplanning.ai.factory import AIClientFactory
from townplanning.ai.models import AIRequest
from townplanning.ai.image_utils import encode_image


IMAGE = "tests/functional/vision/data/sample1.png"


def main():

    client = AIClientFactory.create()

    image = encode_image(IMAGE)

    request = AIRequest(
        system_prompt=(
            "You are a site-plan vision analysis assistant. "
            "Return only valid JSON."
        ),
        user_prompt=(
            "Analyze this site plan. "
            "Identify whether a road is visible. "
            "If a road is visible, describe its location, "
            "label and approximate width."
        ),
        images=[image],
    )

    response = client.generate(request)

    print("SUCCESS:", response.success)

    if response.success:
        print(response.content)
    else:
        print("ERROR:", response.error)


if __name__ == "__main__":
    main()
