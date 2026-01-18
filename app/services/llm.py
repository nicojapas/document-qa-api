from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

class LLMService:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=settings.GEMINI_AI_API_KEY)

    @classmethod
    async def answer_question(cls, question: str, context: list[str]):
        context_text = "\n\n".join(context)
        prompt = f"""
        Answer the question based ONLY on the following context. 
        If the answer is not in the context, say you don't know.
        
        Context: {context_text}
        
        Question: {question}
        """
        response = await cls.llm.ainvoke(prompt)
        
        return response.content
