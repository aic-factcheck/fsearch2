import asyncio
from fact_search.agent import create_graph
from claim_verifier.schemas import ClaimVerifierState, ValidatedClaim

from aic_nlp_utils.json import write_json

async def main():
    validated_claim = ValidatedClaim(
        # claim_text="The Eiffel Tower is taller than 500 meters."
        claim_text="Eiffelova věž má výšku 500 metrů."
        # claim_text="Václav Moravec: Když tedy říkáte, že systém už je nebo podnikáte kroky společně s odbory, aby systém byl uživatelsky komfortnější, konec března tedy splníte jako datum a když říkáte, že jste v mírném předstihu? \n\nJaromír Drábek: Ano, já předpokládám, že ano a já k tomu ale musím dodat to jedno číslo. Samozřejmě, že to nasazení nového systému si vyžádalo zvýšené a velmi zvýšené úsilí pracovníků úřadu práce i ministerstva, ale ta ušetřená miliarda ročně na provozu za to stojí."
        # claim_text="Ivan Bartoš udělal občanku v mobilech."
    )

    state = ClaimVerifierState(claim=validated_claim)

    graph = create_graph()

    i = 1
    async for chunk in graph.astream(
        state,
        stream_mode="updates"
    ):
        for node_name, result in chunk.items():
            write_json(f"{i:02d}_{node_name}.json", result)
        i += 1

if __name__ == "__main__":
    asyncio.run(main())
