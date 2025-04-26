def build_json(text, image_urls):
    # Simpler placeholder logic
    return {
        "response": {
            "book": None,
            "subject": None,
            "chapters": [
                {
                    "chapterName": "Chapter 1",
                    "topics": [
                        {
                            "topicName": "Topic A",
                            "imageUrls": image_urls,
                            "sections": [
                                {
                                    "sectionName": "Section 1",
                                    "content": text[:1000],  # sample text
                                    "imageUrls": []
                                }
                            ],
                            "exercises": []
                        }
                    ],
                    "exercises": []
                }
            ]
        }
    }
