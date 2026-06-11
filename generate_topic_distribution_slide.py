"""Generate a topic-distribution slide for Chinese social media analysis."""

import matplotlib.pyplot as plt


TOPIC_COUNTS = {
    "Scenic spots": 145,
    "Fandom / media": 132,
    "Emotional response": 128,
    "Food": 96,
    "Logistics": 89,
}


def main():
    topics = list(TOPIC_COUNTS.keys())
    counts = list(TOPIC_COUNTS.values())
    total = sum(counts)

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ["#2d7dd2", "#97cc04", "#f45d01", "#474647", "#f4b942"]
    bars = ax.barh(topics, counts, color=colors)

    ax.invert_yaxis()
    ax.set_title("Chinese Social Media Topic Distribution", fontsize=18, fontweight="bold", pad=18)
    ax.set_xlabel("Mention count")
    ax.set_xlim(0, max(counts) * 1.2)

    for bar, count in zip(bars, counts):
        percent = count / total * 100
        ax.text(
            count + max(counts) * 0.02,
            bar.get_y() + bar.get_height() / 2,
            f"{count} ({percent:.1f}%)",
            va="center",
            fontsize=11,
        )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", alpha=0.2)

    plt.tight_layout()
    output = "slide_topic_distribution.png"
    plt.savefig(output, dpi=300, bbox_inches="tight")
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
