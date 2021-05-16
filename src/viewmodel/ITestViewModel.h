// callback class
class A_callback{
    public:
        virtual void onSetValues(int value);
        virtual void onGetValues(int value);
        virtual void onWriteSucess(int timestamp);
}

class B_callback{
    public:
        virtual void onSetValues(int value);
        virtual void onGetValues(int value);
        virtual void onWriteSucess(int timestamp);
}